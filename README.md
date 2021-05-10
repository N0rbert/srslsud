# srslsud

Save/Restore Software List Script for Ubuntu and Debian



This is Python 3 script for my personal needs. Currently it was tested on Ubuntu MATE 18.04 and 20.04 LTS.

Usage scenario is the following: user has two computers. The first computer is old, but has all needed software installed. The second computer is new, user wants to install all the software from first computer on it.

Currently the script supports almost all possible installation sources - Snap, Flatpak, Ubuntu Make and APT. Software lists are saved to JSON file and then maybe be restored/loaded from it.

To enable all the features user needs to install the dependencies using command below:

```bash
# minimal for APT
sudo apt-get install python3 python3-gi python3-apt software-properties-common python3-jsonpickle

# additional for Snap, Flatpak
sudo apt-get install snapd flatpak gir1.2-snapd-1 gir1.2-flatpak-1.0

# additional for Ubuntu Make
sudo apt-get install ubuntu-make
```

After this one can use the following syntax to call `./srslsud.py` with one argument:

- 'snap_save'/'snap_load' (for Snap),
- 'flatpak_save'/'flatpak_load' (for FlatPak),
- 'umake_save'/'umake_load' (for Ubuntu Make),
- 'apt_save'/'apt_load' (for APT),
- 'all_save'/'all_load' (for Snap, Flatpak, Ubuntu Make and APT in one shot).

Please note that JSON files have the following names:

- *snaps.json* for Snap,
- *flatpaks.json* for FlatPak,
- *umake.json* for Ubuntu Make,
- *debs.json* for APT.

'Load' operation for Snap, Flatpak and Ubuntu Make are almost automatic. They require user to enter password only on package installation.

'Load' operation for APT is interactive. The Python script generates Bash script named *apt.sh*. User should manually review this script and then run it by `sudo bash ./apt.sh` and keep an eye on it. Some issues may occur here because of dependencies of something similar. It is recommended to run the 'load' operation on fully upgraded system without PPAs and third-party repositories added. Current version of script support the following repositories: Launchpad PPAs, OpenSuSe Build Service, Oracle VirtualBox, Google Chrome, UbuntuZilla on SourceForge and Yandex Disk.

Quick start:

1. clone this repository on the first machine, install the dependencies, run the script using `./srslsud.py all_save`, copy JSON files and `./srslsud.py` script to removable media;
2. install the dependencies on the second machine with the same OS version, launch the script with `./srslsud.py all_load` from removable media, follow the instructions on screen.

