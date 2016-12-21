python setup.py build; python setup.py install; 
rm -rf build
#rm -rf iotronic.egg-info 
rm -rf dist
cp bin/lightning-rod /usr/bin/
