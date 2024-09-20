# Mininet-Wifi_2024
## Here I will share my research related codes
# MESH topology

conda activate python
Python 3.8.19
pip 24.2 from C:\mycodes\envs\python\lib\site-packages\pip (python 3.8)

when installing ryu remember to-
pip uninstall setuptools
pip install setuptools==67.6.1

Check the port from the controller is listening or not:

`netstat -aon | findstr :6653 `