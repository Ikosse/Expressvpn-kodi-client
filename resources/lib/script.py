import os
import sys
import xbmcaddon
import xbmcgui
import xbmcvfs

from subprocess import TimeoutExpired
from resources.lib.kodiutils import addon_utils, settings_handler, \
        favourites_handler
from resources.lib.countries import country_to_continent
from resources.lib import expressVPN
from resources.lib.expressVPN import ExpressVPNError


dialog = xbmcgui.Dialog()


def run():
    try:
        process_settings()
        main_menu()
    except ExpressVPNError as vpe:
        addon_utils.notification(addon_utils.name, str(vpe))
    except OSError as ose:
        addon_utils.notification(addon_utils.name, str(ose))


def process_settings():
    global _kodi_notify, _kodi_notify_sound, _show_alias, _timeout, _warn_connected

    _kodi_notify = settings_handler.get_setting_as_bool("kodi_notifications")
    _kodi_notify_sound = settings_handler.get_setting_as_bool("kodi_notification_sound")
    _show_alias = settings_handler.get_setting_as_bool("show_alias")
    _timeout = settings_handler.get_setting_as_int("timeout")
    _warn_settings = settings_handler.get_setting("warn_settings")

    try:
        if settings_handler.get_setting_as_bool("auto_connect"):
            expressVPN.set_preference("auto_connect", "true")
        else:
            expressVPN.set_preference("auto_connect", "false")

        if settings_handler.get_setting_as_bool("desktop_notifications"):
            expressVPN.set_preference("desktop_notifications", "true")
        else:
            expressVPN.set_preference("desktop_notifications", "false")

        if settings_handler.get_setting_as_bool("send_diagnostics"):
            expressVPN.set_preference("send_diagnostics", "true")
        else:
            expressVPN.set_preference("send_diagnostics", "false")

        if settings_handler.get_setting_as_bool("force_vpn_dns"):
            expressVPN.set_preference("force_vpn_dns", "true")
        else:
            expressVPN.set_preference("force_vpn_dns", "false")

        if settings_handler.get_setting_as_bool("ipv6_leak_protection"):
            expressVPN.set_preference("disable_ipv6", "true")
        else:
            expressVPN.set_preference("disable_ipv6", "false")

        network_lock = settings_handler.get_setting("network_lock")
        expressVPN.set_preference("network_lock", network_lock)

        protocol = settings_handler.get_setting("preferred_protocol")
        expressVPN.set_preference("preferred_protocol", protocol)

    except ExpressVPNError as vpe:
        if _warn_settings == "notification":
            addon_utils.notification(addon_utils.name, str(vpe))
        elif _warn_settings == "dialog":
            dialog.ok(addon_utils.name, str(vpe))


def main_menu():
    exit_menu = False
    while not exit_menu:
        default_alias = settings_handler.get_setting("default_location")

        header = addon_utils.name
        if expressVPN.is_connected():
            first_item = addon_utils.localize(30000)
            header = "{0} - {1} {2}".format(header,
                                            addon_utils.localize(30001),
                                            expressVPN.connected_location())
        elif expressVPN.is_connecting():
            header = "{0} - {1}".format(header, expressVPN.status())
        else:
            try:
                first_item = "{0} {1}".format(addon_utils.localize(30002),
                    expressVPN.get_location(default_alias))
            except KeyError:
                first_item = "{0} {1}".format(addon_utils.localize(30002),
                                             default_alias)

        choice = xbmcgui.Dialog().select(header, [first_item]
                                         + addon_utils.localize(30003, 30004, 30005))
        if choice == 0:
            if expressVPN.is_connected() or expressVPN.is_connecting():
                disconnect_vpn()
            else:
                connect_vpn(default_alias)
        elif choice == 1:
            server_list_menu()
        elif choice == 2:
            infoVPN()
        else:
            exit_menu = True


def server_list_menu():
    exit_menu = False
    while not exit_menu:
        header = addon_utils.name
        if expressVPN.is_connected():
            header = "{0} - {1} {2}".format(header,
                                            addon_utils.localize(30001),
                                            expressVPN.connected_location())

        choice_list = [".."] + addon_utils.localize(30006, 30007, 30008, 30009)

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
        server_list = favourites_handler.get_servers()

        if _show_alias:
            location_list = ["{0} ({1})".format(server["location"],
                server["alias"]) for server in server_list]
        else:
            location_list = ["{0}".format(server["location"])
                             for server in server_list]

        header = addon_utils.name
        if expressVPN.is_connected():
            header = "{0} - {1} {2}".format(header,
                                            addon_utils.localize(30001),
                                            expressVPN.connected_location())

        choice_list = [".."]  + location_list
        choice = dialog.select(header, choice_list)
        if choice == 0:
            exit_menu = True
        elif choice == -1:
            sys.exit(0)
        else:
            favourites_context_menu(server_list[choice-1]["alias"])


def favourites_context_menu(alias):
    choice = dialog.contextmenu(addon_utils.localize(30010, 30011, 30012, 30013))
    if choice == 0:
        connect_vpn(alias)
    elif choice == 1:
        settings_handler.set_setting("default_location", alias)
    elif choice == 2:
        favourites_handler.remove(alias)
    elif choice == 3:
        clear_favourites = dialog.yesno(addon_utils.name,
                                        addon_utils.localize(30015))
        if clear_favourites:
            favourites_handler.clear()


def server_list_continent_menu():
    exit_menu = False
    while not exit_menu:
        header = addon_utils.name
        if expressVPN.is_connected():
            header = "{0} - {1} {2}".format(header,
                                            addon_utils.localize(30001),
                                            expressVPN.connected_location())

        choice_list = [".."] + addon_utils.localize(30016, 30017, 30018, 30019,
                                                    30020, 30021)

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
        header = addon_utils.name
        if expressVPN.is_connected():
            header = "{0} - {1} {2}".format(header,
                                            addon_utils.localize(30001),
                                            expressVPN.connected_location())

        server_list = expressVPN.list_servers(recommended=recommended)
        alias_list = [server["alias"] for server in server_list if server["alias"] != "smart"]
        location_list = [server["location"] for server in server_list if server["alias"] != "smart"]

        if not recommended: # sort alphabetically
            server_list_sorted = sorted(zip(location_list, alias_list))
            location_list = [location for (location, alias) in server_list_sorted
                             if country_to_continent(location) == continent]
            alias_list = [alias for (location, alias) in server_list_sorted
                          if country_to_continent(location) == continent]

        if _show_alias:
            location_list = ["{0} ({1})".format(location, alias)
                             for (location, alias) in zip(location_list, alias_list)]

        choice_list = [".."] + location_list
        choice = dialog.select(header, choice_list, preselect=choice)

        if choice == 0:
            exit_menu = True
        elif choice == -1:
            sys.exit(0)
        else:
            server_list_context_menu(alias_list[choice-1])


def server_list_context_menu(alias):
    choice = dialog.contextmenu(addon_utils.localize(30010, 30011, 30022))
    if choice == 0:
        connect_vpn(alias)
    elif choice == 1:
        settings_handler.set_setting("default_location", alias)
    elif choice == 2:
        server = {"alias": alias, "location": expressVPN.get_location(alias)}
        favourites_handler.add(server)


def connect_vpn(alias):
    location = expressVPN.get_location(alias)
    old_location = expressVPN.connected_location()
    old_alias = expressVPN.get_alias(old_location)
    addon_utils.notification("{0} {1}...".format(addon_utils.localize(30023),
                                                 location),
                             sound=_kodi_notify_sound, show=_kodi_notify)
    try:
        expressVPN.connect(alias, timeout=_timeout)
        addon_utils.notification("{0} {1}".format(addon_utils.localize(30024),
                                                  location),
                                 sound=_kodi_notify_sound, show=_kodi_notify)

    except ExpressVPNError as vpe:
        if expressVPN.is_connected():
            expressVPN.connected_location
            connect = dialog.yesno(addon_utils.name, "{0} {1} {2} {3} {4}" \
                                   .format(addon_utils.localize(30025),
                                           expressVPN.connected_location(),
                                           addon_utils.localize(30026),
                                           location,
                                           addon_utils.localize(30027)))
            if connect:
                disconnect_vpn()
                connect_vpn(alias)
        else:
            dialog.ok(addon_utils.name, str(vpe))

    except TimeoutExpired as te:
        retry = dialog.yesno(addon_utils.name, addon_utils.localize(30028))
        if retry:
            connect_vpn(alias)


def disconnect_vpn():
    addon_utils.notification(addon_utils.localize(30029), sound=_kodi_notify_sound, show=_kodi_notify)
    try:
        expressVPN.disconnect(timeout=_timeout)
        addon_utils.notification(addon_utils.localize(30030), sound=_kodi_notify_sound, show=_kodi_notify)
    except ExpressVPNError as vpe:
        dialog.ok(addon_utils.name, str(vpe))
    except TimeoutExpired as te:
        retry = dialog.yesno(addon_utils.name, addon_utils.localize(30031))
        if retry:
            disconnect_vpn()


def refreshVPN():
    try:
        expressVPN.refresh(timeout=_timeout)
        dialog.ok(addon_utils.name, addon_utils.localize(30032))
    except ExpressVPNError as vpe:
        dialog.ok(addon_utils.name, str(vpe))
    except TimeoutExpired as te:
        dialog.ok(addon_utils.name, addon_utils.localize(30033))


def infoVPN():
    try:
        info = expressVPN.version()
        dialog.ok(addon_utils.name, info)
    except ExpressVPNError as vpe:
        dialog.ok(addon_utils.name, str(vpe))
