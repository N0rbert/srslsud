#!/usr/bin/python3
"""
Save/Restore Software List Script for Ubuntu and Debian.
Supports various sources - Snap, Flatpak, Ubuntu Make and APT.
"""

import sys
import os
import subprocess
from urllib.parse import urlsplit
import datetime

try:
    import gi
except ImportError:
    print("Error: please install 'python3-gi' deb-package.")
    sys.exit()

try:
    import apt
except ImportError:
    print("Error: please install 'python3-apt' deb-package for APT support.")
    sys.exit()

import aptsources.distro
from aptsources import sourceslist
import apt_pkg

print("This script will save or load software lists installed from various sources: Snap, Flatpak, Ubuntu Make and APT.")

apt_ok = False
if os.access('/usr/bin/add-apt-repository', os.X_OK):
    apt_ok = True
    print("Note: your system supports APT.")
else:
    print("Error: please install 'software-properties-common' deb-package for APT support.")
    sys.exit()

snap_ok = False
if os.access('/usr/bin/snap', os.X_OK):
    snap_ok = True
    print("Note: your system supports Snap.")
else:
    print("Warning: please install 'snapd' deb-package for Snap support!")

flatpak_ok = False
if os.access('/usr/bin/flatpak', os.X_OK):
    flatpak_ok = True
    print("Note: your system supports Flatpak.")
else:
    print("Warning: please install 'flatpak' deb-package for Flatpak support!")

umake_ok = False
if os.access("/usr/bin/umake", os.X_OK) or os.access("/snap/bin/umake", os.X_OK):
    umake_ok = True
    print("Note: your system supports Ubuntu Make.")
else:
    print("Warning: please install 'ubuntu-make' from deb- or snap-package for Ubuntu Make support!")

if snap_ok:
    try:
        gi.require_version('Snapd', '1')
        from gi.repository import Snapd
    except ValueError:
        print("Error: please install 'gir1.2-snapd-1' deb-package for Snap support.")
        sys.exit()

if flatpak_ok:
    try:
        gi.require_version('Flatpak', '1.0')
        from gi.repository import Flatpak
    except ValueError:
        print("Error: please install 'gir1.2-flatpak-1.0' deb-package for Flatpak support.")
        sys.exit()

try:
    import jsonpickle
except Exception:
    print("Error: please install 'python3-jsonpickle' deb-package for JSON file support.")
    sys.exit()

snap_json_filename = 'snaps.json'
flatpak_json_filename = 'flatpaks.json'
umake_json_filename = 'umake.json'
deb_pkg_filename = 'debs.json'
apt_script_file = 'apt.sh'

"""
local functions start
"""

debug_on = False


def save_object(file_name, obj):
    """
    Function for saving object 'obj' to JSON file specified by 'file_name'
    """

    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    with open(file_name, 'w', encoding='utf-8') as f:
        s = jsonpickle.encode(obj)
        f.write(s)


def load_object(file_name):
    """
    Function for loading object from JSON file specified by 'file_name'
    """

    try:
        with open(file_name, encoding='utf-8') as f:
            s = f.read()
            obj = jsonpickle.decode(s)
        return obj
    except Exception:
        print("\tError: unable to open '{}'. Can't continue.".format(file_name))
        sys.exit()


def flatpak_repo_add(name, url):
    """
    Auxilary function for adding Flatpak repository with known 'name' and 'url'.
    Combines several algorithms - simple URL construction with known name and URL,
    and more complicated methods of URL construction.
    """

    flatpak_command = "flatpak remote-add --if-not-exists " + name + " "

    full_repo_url = url.replace("oci+", "") + name + ".flatpakrepo"

    # try remote as URL + .flatpakref
    if subprocess.call(flatpak_command + full_repo_url, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        return 0

    # move .flatpakref to the toplevel
    full_repo_url_split = urlsplit(full_repo_url)
    full_repo_url_toplevel = full_repo_url_split.scheme + '://' + full_repo_url_split.hostname + '/' + full_repo_url_split.path.split('/')[-1]

    if subprocess.call(flatpak_command + full_repo_url_toplevel, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        return 0

    # move .flatpakref to the first level
    full_repo_url_firstlevel = full_repo_url_split.scheme + '://' + full_repo_url_split.hostname + '/' + full_repo_url_split.path.split('/')[1] + '/' + full_repo_url_split.path.split('/')[-1]

    if subprocess.call(flatpak_command + full_repo_url_firstlevel, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        return 0

    # move .flatpakref to the first level, rename folder to flatpak-refs
    full_repo_url_firstlevel_fr = full_repo_url_split.scheme + '://' + full_repo_url_split.hostname + '/flatpak-refs/' + full_repo_url_split.path.split('/')[-1]

    if subprocess.call(flatpak_command + full_repo_url_firstlevel_fr, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        return 0

    # giving up
    return 1


def snap_operations(operation='save'):
    """
    Function for Snap operations
    """

    snap_list = []

    snapd_client = Snapd.Client()
    snapd_client.connect_sync()
    snapd_client.get_system_information_sync()

    print("Will process Snaps using '{}' mode.".format(operation))

    if operation == 'save':
        installed_snaps = snapd_client.list_sync()

        if len(installed_snaps) > 0:
            print("Will now save the list of installed Snaps:")

            for snap in installed_snaps:
                s = dict()
                s['name'] = snap.get_name()
                s['classic'] = (snap.get_confinement() == Snapd.Confinement.CLASSIC)
                s['channel'] = snap.get_channel()
                s['revision'] = snap.get_revision()

                print("\tTitle: " + str(snap.get_title()))
                print("\tClassic?: " + str(s['classic']))
                print("\tName: " + s['name'])
                print("\tChannel: " + s['channel'])
                print("\tRevision: " + s['revision'])
                print("\t---")

                snap_list.append(s)
                save_object(snap_json_filename, snap_list)
        else:
            print("Note: you do not have any Snaps installed.")

    else:  # 'load'
        snap_list = load_object(snap_json_filename)

        if len(snap_list) > 0:
            print("Will now load list of Snaps to install")

            for snap in snap_list:
                print("Trying to install '{}' from '{}' channel at '{}' revision".format(snap['name'], snap['channel'], snap['revision']))

                if snap['classic']:
                    install_flag = Snapd.InstallFlags.CLASSIC
                else:
                    install_flag = Snapd.InstallFlags.NONE

                try:
                    snapd_client.install2_sync(install_flag, snap['name'], snap['channel'], None, None, None, None)
                except Exception as e:
                    print("\t{}".format(e.message))
        else:
            print("Error: can't find any Snaps in the '{}' file.".format(snap_json_filename))

    print("Snap finished.")


def flatpak_operations(operation='save'):
    """
    Function for Flatpak operations
    """

    flatpak_list = []

    flatpak = Flatpak.Installation.new_system()

    print("Will process Flatpaks using '{}' mode.".format(operation))

    if operation == 'save':
        remotes = flatpak.list_remotes()
        if len(remotes) > 0:
            print("Will now save the list of configured Flatpakrefs:")
            for fpr in remotes:
                repos = dict()
                repos['repo-name'] = fpr.get_name()
                repos['repo-url'] = fpr.get_url().replace("oci+", "")
                print("\tRepo name: " + repos['repo-name'])
                print("\tRepo URL: " + repos['repo-url'])
                print("\t---")
                flatpak_list.append(repos)
                save_object(flatpak_json_filename, flatpak_list)
        else:
            print("Note: you do not have any Flatpakrefs configured")

        installed_refs = flatpak.list_installed_refs()
        if len(installed_refs) > 0:
            print("Will now save the list of installed Flatpaks:")
            for fpi in installed_refs:
                f = dict()
                f['name'] = fpi.get_name()
                if fpi.get_kind() == Flatpak.RefKind.RUNTIME:
                    f['kind'] = 'runtime'
                elif fpi.get_kind() == Flatpak.RefKind.APP:
                    f['kind'] = 'application'
                f['arch'] = fpi.get_arch()
                f['branch'] = fpi.get_branch()
                f['origin'] = fpi.get_origin()

                if hasattr(fpi, 'get_appdata_name'):
                    print("\tTitle: " + format(fpi.get_appdata_name()))
                print("\tName: " + f['name'])
                print("\tKind: " + f['kind'])
                print("\tArch: " + f['arch'])
                print("\tBranch: " + f['branch'])
                print("\tOrigin: " + f['origin'])
                print("\t---")

                flatpak_list.append(f)
                save_object(flatpak_json_filename, flatpak_list)
        else:
            print("Note: you do not have any Flatpaks installed.")

    else:  # 'load'
        flatpak_list = load_object(flatpak_json_filename)
        if len(flatpak_list) > 0:
            print("Will now load list of Flatpaks and their remotes to install")

            for fpl in flatpak_list:
                if len(fpl) == 2:
                    print("Flatpak repo record found: '{}' '{}', will try to add it.".format(fpl['repo-name'], fpl['repo-url']))

                    if flatpak_repo_add(fpl['repo-name'], fpl['repo-url']) != 0:
                        print("Error: add '{}' repo failed!".format(fpl['repo-name']))
                    else:
                        flatpak.drop_caches(None)
                        flatpak.update_remote_sync(fpl['repo-name'], None)

                else:
                    print("Trying to install '{}' from '{}' using '{}' branch with '{}'".format(fpl['name'], fpl['origin'], fpl['branch'], fpl['arch']))

                    if fpl['kind'] == 'runtime':
                        kind = Flatpak.RefKind.RUNTIME
                    elif fpl['kind'] == 'application':
                        kind = Flatpak.RefKind.APP

                    try:
                        flatpak.install(fpl['origin'],
                                        kind,
                                        fpl['name'],
                                        fpl['arch'],
                                        fpl['branch'],
                                        None,
                                        None,
                                        None)
                    except Exception as e:
                        print("\t{}".format(e.message))
        else:
            print("Error: can't find any Flatpaks and their remotes in the '{}' file.".format(flatpak_json_filename))

    print("Flatpak finished.")


def umake_operations(operation='save'):
    """
    Function for Ubuntu Make operations
    """

    umake_list = []

    print("Will process Ubuntu Make applications using '{}' mode.".format(operation))
    if operation == 'save':
        umake_cmd = "umake --list-available | grep -E '\[(partially\ |fully\ |)installed\]' | awk -F: '{print $1}'"
        umake_ret, umake_out = subprocess.getstatusoutput(umake_cmd)

        if umake_ret == 0 and umake_out.find("error") == -1:
            if len(umake_out) > 0:
                # parsing umake output - two columns
                # (first with category, second - with program name)
                umake_out_lines = umake_out.split('\n')
                umake_items_raw = []

                for l in umake_out_lines:
                    umake_items_raw.append(l.split('\t'))

                if len(umake_out_lines) > 0 and len(umake_items_raw) > 0:
                    print("Will now save the list of applications installed using Ubuntu Make:")

                    # preparing output list - preserve category for each line
                    for u in umake_items_raw:
                        if len(u) == 1:
                            cat = u[0]
                        elif len(u) == 2:
                            ui = dict()
                            ui['category'] = cat
                            ui['application'] = u[1]
                            print("\tCategory: " + ui['category'])
                            print("\tApplication: " + ui['application'])
                            print("\t---")

                            umake_list.append(ui)
                            save_object(umake_json_filename, umake_list)
            else:
                print("Note: you do not have any applications installed using 'umake'.")
        else:
            print("Error: 'umake' process failed with following message:\n{}.".format(umake_out))

    else:  # 'load'
        umake_list = load_object(umake_json_filename)
        if len(umake_list) > 0:
            print("Will now load list of applications to install using Ubuntu Make:")

            for um in umake_list:
                print("Trying to install '{}' from '{}' category using Ubuntu Make".format(um['application'], um['category']))

                if subprocess.call("umake {} {}".format(um['category'], um['application']), shell=True) != 0:
                    print("Error: installation of '{}' from '{}' category failed!".format(um['application'], um['category']))

        else:
            print("Error: can't find any application in the '{}' file.".format(umake_json_filename))

    print("Ubuntu Make finished.")


# APT functions


def apt_show_package_names_list(p_list):
    """
    Function to show only package names
    """
    o = []
    for p in p_list:
        o.append(p[0])

    return(o)


def apt_show_package_names_dict(p_list):
    """
    Function to show only package names from dictionary
    """
    o = []
    for p in p_list:
        o.append(p['name'])

    return(o)


def apt_key_list():
    """
    This was function is from AptAuth.py ('software-properties' package).
    It calls 'apt-key' utility to get all known repository keys.
    """

    cmd = ["/usr/bin/apt-key", "--quiet", "adv", "--with-colons", "--batch", "--fixed-list-mode", "--list-keys"]
    res = []
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout
    name = ''
    for line in p:
        fields = line.split(":")
        if fields[0] in ["pub", "uid"]:
            name = fields[9]
        if fields[0] == "pub":
            key = fields[4]
            expiry = datetime.date.fromtimestamp(int(fields[5])).isoformat()
        if not name:
            continue
        k = dict()
        k['key'] = key
        k['expiry'] = expiry
        k['name'] = name
        res.append(k)
        name = ''
    p.close()
    return res


def apt_sources_list():
    """
    Function to get the contents of of /etc/apt/sources.list and /etc/apt/sources.list.d/*.list
    """
    sources_list = []

    for s in sourceslist.SourcesList().list:
        s_strip = s.str().strip()
        if s_strip.startswith("deb") and not s_strip.startswith("deb-src"):
            sources_list.append(s_strip.replace("\n", ""))

    return(sources_list)


def apt_parse_debcache(package_list):
    """
    This is adapted code from /usr/share/doc/python-apt-doc/examples/indexfile.py example.
    It parses dependency cache and returns full information about package name and its origin.
    """

    apt_pkg.init()

    sources = apt_pkg.SourceList()
    sources.read_main_list()

    cache = apt_pkg.Cache()
    depcache = apt_pkg.DepCache(cache)

    out_list = []

    for p in package_list:
        pkg = cache[p[0]]
        cand = depcache.get_candidate_ver(pkg)
        for (f, __) in cand.file_list:
            index = sources.find_index(f)
            # print("index: {}".format(index))
            if index:
                if index.label == "Debian Package Index":
                    out_el = dict()
                    out_el['name'] = pkg.name
                    # print(pkg.name)
                    out_el['origin'] = p[1]
                    # print(p[1])
                    # print("archive_uri: {}".format(index.archive_uri("")))
                    out_el['describe'] = index.describe
                    # print("describe: {}".format(index.describe))
                    # print("exists: {}".format(index.exists))
                    # print("has_packages: {}".format(index.has_packages))
                    # print("size: {}".format(index.size))
                    # print("is_trusted: {}".format(index.is_trusted))
                    # print("- - -\n")
                    out_list.append(out_el)

    return out_list


def apt_remove_word_from_brackets_in_sources_list(st, wordtoremove):
    """
    Function for removing word 'signed-by' from deb-url lines like
    "deb [signed-by=/usr/share/keyrings/docker-archive-keyring.gpg arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
    to transform such line to
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
    so have only CPU architecture
    """
    ss = st.split("]")

    if len(ss) == 2:
        sss = ss[0].split()
        for sb in sss:
            if wordtoremove in sb:
                sss.remove(sb)

        st = ' '.join(sss) + "]" + ss[1]

        if "[" not in st:
            t = st.split()
            t[1] = "[" + t[1]
            st = ' '.join(t)

    return(st)


def apt_add_deb_url_to_deb_info(deb_info, sources_list):
    """
    Function to add special 'deb-url' field to the package info structure.
    Also it calls the auxiliary function to remove "signed-by" from 'deb-url'.
    """

    for t in deb_info:
        ds = t['describe'].split(" ")[0]

        for s in sources_list:
            if ds in s:
                t['deb-url'] = apt_remove_word_from_brackets_in_sources_list(s, "signed-by")

        debug_on and print("{}: {}".format(t['name'], t['deb-url']))

    return deb_info


def apt_get_ppa_shortcut(url):
    """
    Function to transform full deb-url for PPA to 'ppa:username/ppa-name' shortcut.
    """

    ppa_split = url.split("ppa.launchpad.net/")[1].split("/", 2)
    ppa_shortcut = ""
    if len(ppa_split) >= 2:
        ppa_shortcut = "ppa:" + ppa_split[0] + "/" + ppa_split[1]

    return ppa_shortcut


def extract_unique_elements(elements_list, repo_key_name):
    """
    Function to collect unique elements with known key in the new list
    """
    out_list = []

    for el in elements_list:
        if el[repo_key_name] not in out_list:
            out_list.append(el[repo_key_name])

    return out_list


def append_command_to_script(filename, command):
    """
    Function for appending lines to the file with known filename
    """
    with open(filename, mode='a+') as fsh:
        fsh.write(command + "\n")


def apt_operations(operation='save'):
    """
    Function for APT operations

    TODO: pin-file processing
    """

    # 1. Detecting operating system
    distro = aptsources.distro.get_distro()
    if isinstance(distro, aptsources.distro.UbuntuDistribution):
        distro_name = 'Ubuntu'
        print("You are running {} {} ({}) distro.".format(distro_name, distro.release, distro.codename))
    elif isinstance(distro, aptsources.distro.DebianDistribution):
        distro_name = 'Debian'
        print("You are running {} {} ({}) distro.".format(distro_name, distro.release, distro.codename))
    else:
        print("Error: your distro '{}' is not supported!".format(distro))

    print("Will process deb-packaged applications using '{}' mode.".format(operation))
    if operation == 'save':
        # 2. Installed packages part - listing them and arranging
        # next four lines are taken from: https://unix.stackexchange.com/a/369653/65781
        apt_cache = apt.Cache()

        manual = set(pkg for pkg in apt_cache if pkg.is_installed and not pkg.is_auto_installed)
        depends = set(dep_pkg.name for pkg in manual for dep in pkg.installed.get_dependencies('PreDepends', 'Depends', 'Recommends') for dep_pkg in dep)

        installed = sorted([pkg.name for pkg in manual if pkg.name not in depends])

        print("Total number of manually installed packages: {}.".format(len(installed)))

        # sorting installed packages
        pkg_ubuntu = list()
        pkg_thirdparty_ppa = list()
        pkg_thirdparty_deb = list()
        pkg_local = list()

        for i in installed:
            pkg = apt_cache[i]
            o = pkg.installed.origins[0]
            if o.origin == 'Ubuntu':
                pkg_ubuntu.append([pkg.name, o])
            if o.origin != "Ubuntu" and o.archive != 'now' and o.trusted and o.origin.startswith("LP-PPA"):
                # print(pkg)
                # print("\t{}".format(o))
                # print("- - -\n")
                pkg_thirdparty_ppa.append([pkg.name, o])
            if o.origin != "Ubuntu" and o.archive != 'now' and o.trusted and not o.origin.startswith("LP-PPA"):
                # print(pkg)
                # print("\t{}".format(o))
                # print("- - -\n")
                pkg_thirdparty_deb.append([pkg.name, o])
            if o.archive == 'now' or not o.trusted:
                pkg_local.append(pkg.name)

        # listing installed packages

        print("\n\nPackages installed from official Ubuntu repositories ({}):".format(len(pkg_ubuntu)))
        print(apt_show_package_names_list(pkg_ubuntu))

        print("\n\nPackages installed from thirdparty PPA repositories ({}):".format(len(pkg_thirdparty_ppa)))
        print(apt_show_package_names_list(pkg_thirdparty_ppa))

        print("\n\nPackages installed from thirdparty deb-repositories ({}):".format(len(pkg_thirdparty_deb)))
        print(apt_show_package_names_list(pkg_thirdparty_deb))

        print("\n\nPackages installed from local deb-files ({}):".format(len(pkg_local)))
        print(pkg_local)

        print("\n\nList of trusted keys from apt-key:")
        apt_keys = apt_key_list()
        print(apt_keys)

        # 3. Getting contents of sources.list and sources.list.d/*.list files of currently running system

        print("\n\nContents of /etc/apt/sources.list and /etc/apt/sources.list.d/:")
        sources_list = apt_sources_list()
        print(sources_list)

        # 4. Finding package origins and locate them in sources.list files

        print("\n\nWill now calculate the dependencies for all installed packages.")

        debug_on and print("\n\nWill now show the origins of official packages:")
        pkg_ubuntu_info = apt_parse_debcache(pkg_ubuntu)
        debug_on and print(pkg_ubuntu_info)

        debug_on and print("\n\nWill now show the origins of thirdparty PPA packages:")
        pkg_thirdparty_ppa_info = apt_parse_debcache(pkg_thirdparty_ppa)
        debug_on and print(pkg_thirdparty_ppa_info)

        debug_on and print("\n\nWill now show the origins of thirdparty deb packages:")
        pkg_thirdparty_deb_info = apt_parse_debcache(pkg_thirdparty_deb)
        debug_on and print(pkg_thirdparty_deb_info)

        debug_on and print("\n\ndeb-url for PPAs:")
        pkg_thirdparty_ppa_info = apt_add_deb_url_to_deb_info(pkg_thirdparty_ppa_info, sources_list)

        if debug_on:
            print("\nppa names for PPAs:")
            for p in pkg_thirdparty_ppa_info:
                print("\t" + apt_get_ppa_shortcut(p['deb-url']))

        debug_on and print("\n\ndeb-url for third-party repositories:")
        pkg_thirdparty_deb_info = apt_add_deb_url_to_deb_info(pkg_thirdparty_deb_info, sources_list)

        # 6. Preparing data for JSON
        deb_pkg_list = dict()
        deb_pkg_list['distro'] = distro
        deb_pkg_list['package_stats'] = {'total': len(installed), 'official': len(pkg_ubuntu), 'ppas': len(pkg_thirdparty_ppa), 'thirdparty': len(pkg_thirdparty_deb), 'local': len(pkg_local)}
        deb_pkg_list['official_packages'] = []
        deb_pkg_list['launchpad_ppa_packages'] = []
        deb_pkg_list['thirdparty_packages'] = []
        deb_pkg_list['thirdparty_keys'] = []
        deb_pkg_list['local_packages'] = pkg_local

        for op in pkg_ubuntu_info:
            op_info = dict()
            op_info['name'] = op['name']
            op_info['component'] = op['origin'].component
            op_info['archive'] = op['origin'].archive
            deb_pkg_list['official_packages'].append(op_info)

        for lpp in pkg_thirdparty_ppa_info:
            lpp_info = dict()
            lpp_info['name'] = lpp['name']
            lpp_info['repo'] = apt_get_ppa_shortcut(lpp['deb-url'])
            deb_pkg_list['launchpad_ppa_packages'].append(lpp_info)

        # 5. Key management for thirdparty deb-repositories
        for p in pkg_thirdparty_deb_info:
            # debug_on and print("app: {}".format(p))

            tp_info = dict()
            tp_info['name'] = p['name']
            tp_info['repo'] = p['deb-url']
            deb_pkg_list['thirdparty_packages'].append(tp_info)

            for k in apt_keys:
                if not k['name'].startswith("Launchpad"):
                    # print("\tkey: {}".format(k['name']))

                    e1 = k['name'] in p['name']
                    e2 = p['name'] in k['name']
                    e3 = len(p['origin'].origin) > 0 and p['origin'].origin in k['name']
                    e4 = len(p['origin'].label) > 0 and p['origin'].label in k['name']
                    e5 = len(p['origin'].label) > 0 and k['name'] in p['origin'].label
                    e6 = False  # OpenSuSe Build Service
                    e7 = p['name'].replace("-", " ") in k['name'].lower()  # Yandex Disk

                    if "build.opensuse.org" in k['name']:
                        # debug_on and print("{} is OBS".format(k))
                        if "home\\x" in k['name']:
                            obs_repo_user = bytes(k['name'], encoding='utf-8').decode("unicode_escape").replace("home:", "home:/").split(" ")[0]
                            # debug_on and print(obs_repo_user)
                            e6 = obs_repo_user in p['deb-url']
                        else:
                            obs_repo_user = k['name'].split(" ")[0]
                            # debug_on and print(obs_repo_user)
                            e6 = obs_repo_user in p['deb-url']

                    if e1 or e2 or e3 or e4 or e5 or e6 or e7:
                        debug_on and print("\t\tkey for '{}' seems to be found as {}".format(p['name'], k))
                        tpk = dict()
                        tpk['name'] = p['name']
                        tpk['key'] = k
                        deb_pkg_list['thirdparty_keys'].append(tpk)

        # 6. Saving package information to JSON
        print("\n\nSaving packages list to the '{}' file.".format(deb_pkg_filename))
        debug_on and print(deb_pkg_list)
        save_object(deb_pkg_filename, deb_pkg_list)

    else:  # 'load'
        print("Will now load list of deb-packages to install.")

        with open(apt_script_file, 'w') as fsh:
            fsh.close()

        deb_pkg_list = load_object(deb_pkg_filename)

        if deb_pkg_list['distro'].codename == distro.codename and deb_pkg_list['distro'].id == distro.id:

            print("The file contains information about {} manually installed packages to install.".format(deb_pkg_list['package_stats']['total']))

            if deb_pkg_list['package_stats']['total'] > 0:
                append_command_to_script(apt_script_file, "#!/bin/bash")
                append_command_to_script(apt_script_file, "lsb_release -cs | grep -q '" + distro.codename + "' || { echo 'Error: you are running different system version. Script will stop.'; exit; }")

                if deb_pkg_list['package_stats']['official'] > 0:
                    print("\n\nThe file contains list of the following {} official deb-packages:".format(deb_pkg_list['package_stats']['official']))
                    print(apt_show_package_names_dict(deb_pkg_list['official_packages']))

                    # adding commands to installation script for official packages
                    append_command_to_script(apt_script_file, "dpkg --add-architecture i386")

                    for c in extract_unique_elements(deb_pkg_list['official_packages'], 'component'):
                        append_command_to_script(apt_script_file, "add-apt-repository {}".format(c))

                    append_command_to_script(apt_script_file, "apt-get update")

                    off_pkgs = ' '.join(extract_unique_elements(deb_pkg_list['official_packages'], 'name'))
                    append_command_to_script(apt_script_file, "apt install {}".format(off_pkgs))

                if deb_pkg_list['package_stats']['ppas'] > 0:
                    print("\n\nThe file contains list of the following {} packages from PPAs:".format(deb_pkg_list['package_stats']['ppas']))
                    print(apt_show_package_names_dict(deb_pkg_list['launchpad_ppa_packages']))

                    # adding command to installation script for PPAs
                    for ppa in extract_unique_elements(deb_pkg_list['launchpad_ppa_packages'], 'repo'):
                        append_command_to_script(apt_script_file, "add-apt-repository {}".format(ppa))

                    append_command_to_script(apt_script_file, "apt-get update")

                    ppa_pkgs = ' '.join(extract_unique_elements(deb_pkg_list['launchpad_ppa_packages'], 'name'))
                    append_command_to_script(apt_script_file, "apt install {}".format(ppa_pkgs))

                if deb_pkg_list['package_stats']['thirdparty'] > 0:
                    print("\n\nThe file contains list of the following {} packages from third-party repositories:".format(deb_pkg_list['package_stats']['thirdparty']))
                    print(apt_show_package_names_dict(deb_pkg_list['thirdparty_packages']))

                    # adding command to installation script for third-party deb-repositories
                    for tpk in extract_unique_elements(deb_pkg_list['thirdparty_keys'], 'key'):
                        append_command_to_script(apt_script_file, "apt-key adv --keyserver keyserver.ubuntu.com --recv {}".format(tpk['key']))

                    for tpr in extract_unique_elements(deb_pkg_list['thirdparty_packages'], 'repo'):
                        append_command_to_script(apt_script_file, "add-apt-repository '{}'".format(tpr))

                    append_command_to_script(apt_script_file, "apt-get update")

                    tpr_pkgs = ' '.join(extract_unique_elements(deb_pkg_list['thirdparty_packages'], 'name'))
                    append_command_to_script(apt_script_file, "apt install {}".format(tpr_pkgs))

                if deb_pkg_list['package_stats']['local'] > 0:
                    print("\n\nThe file contains list of the following {} locally installed packages:".format(deb_pkg_list['package_stats']['local']))
                    print(deb_pkg_list['local_packages'])
                    print("Note: this script can't really guess the origin of these packages, so you have to download them by yourself.")

                print("\n\nAll installation commands were written into '{}' file.".format(apt_script_file))
                print("You can review its contents and then interactively run it using 'sudo bash ./{}'.".format(apt_script_file))

        else:  # wrong distro and codename
            print("Error: JSON file was created for {} {}, but you are now using {} {}. This is not supported. Script will stop.".format(deb_pkg_list['distro'].codename, deb_pkg_list['distro'].id, distro.codename, distro.id))

    print("APT finished.")


"""
/local functions end
"""

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        op = sys.argv[1]

        if op == 'snap_save':
            if snap_ok:
                snap_operations('save')
        elif op == 'snap_load':
            if snap_ok:
                snap_operations('load')
        elif op == 'flatpak_save':
            if flatpak_ok:
                flatpak_operations('save')
        elif op == 'flatpak_load':
            if flatpak_ok:
                flatpak_operations('load')
        elif op == 'umake_save':
            if umake_ok:
                umake_operations('save')
        elif op == 'umake_load':
            if umake_ok:
                umake_operations('load')
        elif op == 'apt_save':
            if apt_ok:
                apt_operations('save')
        elif op == 'apt_load':
            if apt_ok:
                apt_operations('load')
        elif op == 'all_save':
            if snap_ok:
                snap_operations('save')
            if flatpak_ok:
                flatpak_operations('save')
            if umake_ok:
                umake_operations('save')
            if apt_ok:
                apt_operations('save')
        elif op == 'all_load':
            if snap_ok:
                snap_operations('load')
            if flatpak_ok:
                flatpak_operations('load')
            if umake_ok:
                umake_operations('load')
            if apt_ok:
                apt_operations('load')
        else:
            print("Error: option '{}' is not supported.".format(op))

    else:
        print("\nUsage {} with one argument:\n - 'snap_save'/'snap_load' (for Snap),\n - 'flatpak_save'/'flatpak_load' (for FlatPak),\n - 'umake_save'/'umake_load' (for Ubuntu Make),\n - 'apt_save'/'apt_load' (for APT),".format(sys.argv[0]))
        print(" - 'all_save'/'all_load' (for Snap, Flatpak, Ubuntu Make and APT in one shot).")
