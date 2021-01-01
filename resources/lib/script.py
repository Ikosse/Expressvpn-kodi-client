#-*- coding: utf-8 -*-

from resources.lib import kodiutils
from resources.lib import kodilogging
from resources.lib.countries import country_to_continent
from resources.lib import expressVPN
from resources.lib.expressVPN import ExpressVPNError, TimeoutExpired
import os
import sys
import errno
import logging
import xbmcaddon
import xbmcgui


ADDON = xbmcaddon.Addon()
addon_name = ADDON.getAddonInfo('name')
addon_path = ADDON.getAddonInfo('path')
logger = logging.getLogger(ADDON.getAddonInfo('id'))
dialog = xbmcgui.Dialog()


def run(): 
    try:
        process_settings()
        main_menu()
    except ExpressVPNError as vpe:
        kodiutils.notification(addon_name, str(vpe))
    except OSError as ose:
        kodiutils.notification(addon_name, str(ose))


def process_settings():
    global _kodi_notify, _kodi_notify_sound, _show_alias, _timeout, _warn_connected

    _kodi_notify = kodiutils.get_setting_as_bool('kodi_notifications')
    _kodi_notify_sound = kodiutils.get_setting_as_bool('kodi_notification_sound')
    _show_alias = kodiutils.get_setting_as_bool('show_alias')
    _timeout = kodiutils.get_setting_as_int('timeout')
    _warn_settings = kodiutils.get_setting('warn_settings')

    try:
        if kodiutils.get_setting_as_bool('auto_connect'):
            expressVPN.set_preference('auto_connect', 'true')
        else:
            expressVPN.set_preference('auto_connect', 'false')

        if kodiutils.get_setting_as_bool('desktop_notifications'):
            expressVPN.set_preference('desktop_notifications', 'true')
        else:
            expressVPN.set_preference('desktop_notifications', 'false')

        if kodiutils.get_setting_as_bool('send_diagnostics'):
            expressVPN.set_preference('send_diagnostics', 'true')
        else:
            expressVPN.set_preference('send_diagnostics', 'false')

        if kodiutils.get_setting_as_bool('force_vpn_dns'):
            expressVPN.set_preference('force_vpn_dns', 'true')
        else:
            expressVPN.set_preference('force_vpn_dns', 'false')
                          
        if kodiutils.get_setting_as_bool('ipv6_leak_protection'):
            expressVPN.set_preference('disable_ipv6', 'true')
        else:
            expressVPN.set_preference('disable_ipv6', 'false')
            
        network_lock = kodiutils.get_setting('network_lock')
        expressVPN.set_preference('network_lock', network_lock)

        protocol = kodiutils.get_setting('preferred_protocol')
        expressVPN.set_preference('preferred_protocol', protocol)

    except ExpressVPNError as vpe:
        if _warn_settings == "notification":
            kodiutils.notification(addon_name, str(vpe))
        elif _warn_settings == "dialog":
            dialog.ok(addon_name, str(vpe))


def main_menu():
    exit_menu = False
    while not exit_menu:
        default_alias = kodiutils.get_setting('default_location')

        header = addon_name
        if expressVPN.is_connected():
            first_item = "Disconnect"
            header = header + " - connected to " + expressVPN.connected_location()
        elif expressVPN.is_connecting():
            first_item = "Disconnect"
            header = header + " - " + expressVPN.status()
        else:
            try:
                first_item = "Connect to " + expressVPN.alias_location(default_alias)
            except KeyError:
                first_item = "Connect to " + default_alias

        choice = xbmcgui.Dialog().select(header, [first_item, 'List servers', 'Settings', 'About', 'Exit'])
        
        if choice == 0:
            if expressVPN.is_connected() or expressVPN.is_connecting():
                disconnectVPN()
            else:
                connectVPN(default_alias)
        elif choice == 1:
            server_list_menu()
        elif choice == 2:
            kodiutils.show_settings()
            process_settings()
        elif choice == 3:
            infoVPN()
        else:
            exit_menu = True


def server_list_menu():
    exit_menu = False
    while not exit_menu:
        header = addon_name
        if expressVPN.is_connected():
            header = header + " - connected to " + expressVPN.connected_location()

        choice_list = [".."] + ["All"] + ["Favourites"] + ["Recommended"] + ["refresh"]

        choice = dialog.select(header, choice_list)      
        if choice == 0:
            exit_menu = True
        elif choice == 1:
           server_list_continent_menu() 
        elif choice == 2:
            favourites_menu()
        elif choice == 3:
           server_list_country_menu(recommended=True) 
        elif choice == 4:
            refreshVPN()
        else:
            sys.exit(0)


def favourites_menu():
    exit_menu = False
    while not exit_menu: 
        alias_list = []
        try:
            with open(addon_path + "/resources/favourites.txt", "r") as fh:
                for alias in fh:
                    alias_list.append(alias.strip("\n"))
        except EnvironmentError as e:
            if e.errno != errno.ENOENT:
                raise

        location_dict = expressVPN.location_dictionary()
        location_list = [location_dict[alias] for alias in alias_list]

        if _show_alias:
            location_list = [location_list[i] + " (" + alias_list[i]  + ")" for i in range(len(location_list))]

        header = addon_name
        if expressVPN.is_connected():
            header = header + " - connected to " + expressVPN.connected_location()
            
        choice_list = [".."] + ["clear"] + location_list + ["back to top"]
        choice = dialog.select(header, choice_list)      
        if choice == 0:
            exit_menu = True

        elif choice == 1:
            clear_favourites = dialog.yesno(addon_name, "Are you sure you want to clear all favourites?")
            if clear_favourites:
                try:
                    os.remove(addon_path + "/resources/favourites.txt")
                except EnvironmentError as e:
                    if e.errno != errno.ENOENT:
                        raise

        elif choice == -1:
            sys.exit(0)

        elif choice == len(choice_list)-1:
            choice = 0

        else:
            favourites_context_menu(alias_list[choice-2])


def favourites_context_menu(alias):
    choice = dialog.contextmenu(["connect", "set as default", "remove", "back"])
    if choice == 0:
        connectVPN(alias)
    elif choice == 1:
        kodiutils.set_setting('default_location', alias)
    elif choice == 2:
        remove_from_favourites(alias)


def add_to_favourites(alias):
    try: 
        with open(addon_path + "/resources/favourites.txt", "a+") as fh:
            for line in fh:
                if line.strip("\n") == alias:
                    return
            fh.write(alias + "\n")
    except EnvironmentError as e:
        if e.errno != errno.ENOENT:
            raise


def remove_from_favourites(alias):
    try:
        with open(addon_path + "/resources/favourites.txt", "r") as fh:
            lines = fh.readlines()

        with open(addon_path + "/resources/favourites.txt", "w") as fh:
            for line in lines:
                if line.strip("\n") != alias:
                    fh.write(line)
    except EnvironmentError as e:
        if e.errno != errno.ENOENT:
            raise


def server_list_continent_menu():
    exit_menu = False
    while not exit_menu:
        header = addon_name
        if expressVPN.is_connected():
            header = header + " - connected to " + expressVPN.connected_location()

        choice_list = [".."] + ["Europe"] + ["Asia"] + ["North America"] + ["South America"] + ["Africa"] + ["Oceania"]

        choice = dialog.select(header, choice_list)      
        if choice == 0:
            exit_menu = True
        elif choice == -1:
            sys.exit(0)
        else:
           server_list_country_menu(continent=choice_list[choice], recommended=False) 


def server_list_country_menu(continent=None, recommended=True):
    exit_menu = False
    choice = 0
    while not exit_menu:
        header = addon_name
        if expressVPN.is_connected():
            header = header + " - connected to " + expressVPN.connected_location()

        server_list = expressVPN.list_servers(recommended=recommended)
        alias_list = [tup[0] for tup in server_list if tup[0] != "smart"]        
        location_list = [tup[1] for tup in server_list if tup[0] != "smart"]        

        if not recommended:
            server_list_sorted = sorted(zip(location_list, alias_list))
            location_list = [tup[0] for tup in server_list_sorted if country_to_continent(tup[0]) == continent]
            alias_list = [tup[1] for tup in server_list_sorted if country_to_continent(tup[0]) == continent]

        if _show_alias:
            location_list = [location_list[i] + " (" + alias_list[i]  + ")" for i in range(len(location_list))]

        choice_list = [".."] + location_list + ["back to top"]
        choice = dialog.select(header, choice_list, preselect=choice)      

        if choice == 0:
            exit_menu = True
        elif choice == -1:
            sys.exit(0)
        elif choice == len(choice_list)-1:
            choice = 0
        else:
            server_list_context_menu(alias_list[choice-1])


def server_list_context_menu(alias):
    choice = dialog.contextmenu(["connect", "set as default", "add to favourites", "back"])
    if choice == 0:
        connectVPN(alias)
    elif choice == 1:
        kodiutils.set_setting('default_location', alias)
    elif choice == 2:
        add_to_favourites(alias)


def connectVPN(server_alias):
    try:
        location = expressVPN.alias_location(server_alias)
    except KeyError:
        location = server_alias

    process_settings() # ensure settings are set before connecting

    kodiutils.notification("connecting to " + location + "...", sound=_kodi_notify_sound, show=_kodi_notify)
    try:
        expressVPN.connect(server_alias, timeout=_timeout)
        kodiutils.notification("connected to " + location, sound=_kodi_notify_sound, show=_kodi_notify)

    except ExpressVPNError as vpe:
        if expressVPN.is_connected():
            connect = dialog.yesno(addon_name, "You are already connected, do you wish to disconnect from " + expressVPN.connected_location() + " and connect to " + location + " instead?")
            if connect:
                disconnectVPN()
                connectVPN(server_alias) 
        else:
            dialog.ok(addon_name, str(vpe))

    except TimeoutExpired as te:
        retry = dialog.yesno(addon_name, "Connection attempt timed out, do you wish to retry? ")
        disconnectVPN()
        if retry:
            connectVPN(server_alias)


def disconnectVPN():
    kodiutils.notification("disconnecting...", sound=_kodi_notify_sound, show=_kodi_notify)
    try:
        expressVPN.disconnect(timeout=_timeout)
        kodiutils.notification("disconnected", sound=_kodi_notify_sound, show=_kodi_notify)
    except ExpressVPNError as vpe:
        dialog.ok(addon_name, str(vpe))
    except TimeoutExpired as te:
        retry = dialog.yesno(addon_name, "Disconnection attemp timed out, do you wish to retry?")
        if retry:
            disconnectVPN()


def refreshVPN():
    try:
        expressVPN.refresh(timeout=_timeout)
        dialog.ok(addon_name, "Refreshed server list, note that this is done automatically every 3 hours.")
    except ExpressVPNError as vpe:
        dialog.ok(addon_name, str(vpe))
    except TimeoutExpired as te:
        dialog.ok(addon_name, "Refresh server list timed out.")


def infoVPN():
    try:
        info = expressVPN.version()
        dialog.ok(addon_name, info)
    except ExpressVPNError as vpe:
        dialog.ok(addon_name, str(vpe))
