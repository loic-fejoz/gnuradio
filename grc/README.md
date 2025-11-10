# GNURadio Companion

## How to start development environment

```sh
git clone...
cd gnuradio
python3 -m venv .venv
source .venv/bin/activate
pip install pycairo PyGObject
sudo apt install python3-gi
export PYTHONPATH=`realpath ".venv/lib/python3.13/site-packages/"`:`pwd`:/usr/lib/python3/dist-packages/
export GR_DONT_LOAD_PREFS=1
export GRC_BLOCKS_PATH=`realpath "grc/blocks"`
```

```sh
 ./scripts/gnuradio-companion --qt
```