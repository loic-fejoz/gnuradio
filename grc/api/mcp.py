from fastmcp import FastMCP
## from grc.gui_qt.components.window import MainWindow

import time
from typing import (Any, List, OrderedDict, Dict)
from grc.core.FlowGraph import FlowGraph
from grc.core.platform import Platform
from grc.gui_qt.components.block_library import BlockLibrary
from grc.gui_qt.components.canvas.flowgraph import FlowgraphScene

class GRCMCP(FastMCP):
    main_window: None

    @property
    def currentFlowgraph(self) -> FlowGraph:
        return mcp.main_window.currentFlowgraph # type: ignore
    
    @property
    def currentFlowgraphScene(self) -> FlowgraphScene:
        return mcp.main_window.currentFlowgraphScene # type: ignore
    
    @property
    def platform(self) -> Platform:
        return mcp.main_window.platform # type: ignore

    def export_simplified_data(self) -> OrderedDict[str, Any]:
        data = self.currentFlowgraph.export_data()
        new_options = {
            'parameters': {
                'id': data['options']['parameters']['id'],
                'title': data['options']['parameters']['title'],
            }
        }
        data['options'] = new_options
        del data['metadata']
        for blk in data['blocks']:
            del blk['states']
            # Do not output parameters...
            params = blk['parameters']
            del blk['parameters']
            # ...except for some blocks, still keep some parameters
            if blk['id'] == 'variable':
                blk['parameters'] = {
                    'value': params.get('value', None)
                }
            elif blk['id'].startswith('soapy_'):
                blk['parameters'] = {
                    'center_freq': params.get('center_freq', None),
                    'samp_rate': params.get('samp_rate', None),
                    'type': params.get('type', None)
                }
        return data

mcp = GRCMCP("GNURadio Companion")

@mcp.resource("config://version")
def get_version(): 
    return mcp.platform.config.version

@mcp.tool
def create_flowgraph(title: str, description: str):
    """Create a new flowgraph with given title and description."""
    current_fg = str(mcp.currentFlowgraph)
    print(f'current_fg: {current_fg}')
    mcp.main_window.actions['new'].trigger()
    # Actively wait for the new graph to be created
    while current_fg == str(mcp.currentFlowgraph):
        print('current_fg:', str(mcp.currentFlowgraph))
        time.sleep(0.100)
    fg = mcp.currentFlowgraph
    fg.options_block.params['title'].value = title
    fg.options_block.params['description'].value = description
    # mcp.main_window.actions['reload'].trigger()
    return f'created {str(fg)}'

@mcp.tool
def get_current_flowgraph():
    """ Get full content of the currently selected flowgraph as a dictionary.
    The dictionary contains all the information about `blocks` and `connections`.
    """
    fg = mcp.currentFlowgraph
    return fg.export_data()

@mcp.tool
def get_simplified_current_flowgraph():
    """ Get content of the currently selected flowgraph as a dictionary.
    The dictionary contains a simplified subset of information about `blocks` and `connections`.
    """
    return mcp.export_simplified_data()

@mcp.tool
def partial_update_flowgraph(patchs: List[OrderedDict[str, Any]]) -> List[OrderedDict[str, Any]]:
    """
    Appliquer un patch partiel au flowgraph (style JSON Patch)

    Supported operations:
    - add_block : ajouter un ou plusieurs blocs
    - remove_block : supprimer des blocs
    - update_block : modifier les paramètres d'un bloc
    - add_connection : créer des connexions
    - remove_connection : supprimer des connexions

    For example, adding a new variable `samp_rate` is:

    ```json
    [
        {
            "op": "add_block",
            "value": {
                "id": "variable",
                "name": "samp_rate",
                "parameters": {
                    "value": "768000"
                }
            }
        }
    ]
    ```

    """
    fg = mcp.currentFlowgraph
    result=[]
    for patch_op in patchs:
        # Map and normalize actions
        if patch_op['op'] == 'add' and patch_op.get('path', '').startswith('/block'):
            # map `add /block(s)?/foo`
            patch_op['op'] = 'add_block'
            path = patch_op['path'].split('/')
            if len(path) > 2:
                name = patch_op['path'] = path[2]
                value = patch_op.get('value', {})
                if 'name' not in value:
                    value['name'] = name
        elif patch_op['op'] == 'remove' and patch_op.get('path', '').startswith('/block'):
            patch_op['op'] = 'remove_block'
            patch_op['path'] = patch_op['path'].split('/')[2]

        # Handle actions
        if patch_op['op'] == 'add_block':
            value = patch_op.get('value', {})
            block_id = value.get('id', None)
            # new_blk = fg.new_block(block_id)
            new_blk = mcp.currentFlowgraphScene.add_block(block_id)
            if new_blk:
                params = value.get('parameters', {})
                # if 'name' in value:
                #     new_blk.params['name'].value = value['name']
                result.append({'status': f'block {block_id} created: {str(new_blk)}'})
            else:
                result.append({'status': f'failed to create block {block_id}'})

        elif patch_op['op'] == 'remove_block':
            block_name = patch_op.get('path', None)
            try:
                blk_to_remove = fg.get_block(block_name)
            except KeyError:
                blk_to_remove = None
            if blk_to_remove:
                try:
                    fg.remove_element(blk_to_remove)
                    mcp.currentFlowgraphScene.update()
                    result.append({'status': f'block {block_name} removed'})
                except:
                    result.append({'status': f'failed to remove block {block_name}'})
            else:
                result.append({'status': f'failed to remove unknown block {block_name}'})
        else:
            result.append({'status': 'patch operation ignored', 'op': patch_op})
    return result

@mcp.tool
def list_available_blocks(category_filter: str | None = None):
    """
    Lister tous les blocs GNU Radio disponibles, avec filtrage possible par catégorie
    Catégories : sources, sinks, filters, modulators, demodulators, etc.
    Retourner : nom, description courte, catégorie
    """
    blocks = mcp.platform.blocks
    if category_filter:
        blocks = [blk for _, blk in blocks.items() if blk.category == category_filter]
    else:
        blocks = [blk for _, blk in blocks.items()]
    print(blocks)
    return [{
        'key': blk.key,
        'label': blk.label,
        'category': blk.category,
        # 'documentation': blk.documentation,
        'doc_url': blk.doc_url,
        # 'input_datas': blk.inputs_data,
        # 'output_datas': blk.output_datas,
    } for _, blk in enumerate(blocks)]
    

@mcp.tool
def get_block_info(key: str) -> Dict[str, Any]:
    """Obtenir la documentation détaillée d'un bloc spécifique
    Paramètres requis/optionnels, types, valeurs par défaut, description complète
    Types de ports (entrée/sortie)
    """
    blk = mcp.platform.blocks.get(key, None)
    if not blk:
        return {'error': 'Block information not found', 'key': key}
    return {
        'key': blk.key,
        'label': blk.label,
        'category': blk.category,
        'documentation': blk.documentation,
        'doc_url': blk.doc_url,
        'input_datas': blk.inputs_data,
        'output_datas': blk.outputs_data,
    }

def attach(main_window) -> GRCMCP:
    mcp.main_window = main_window
    return mcp