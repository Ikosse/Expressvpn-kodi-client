# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import sys
import json


class AddonUtils():

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.id = self.addon.getAddonInfo("id")
        self.name = self.addon.getAddonInfo("name")
        self.url = sys.argv[0]

        self.path = xbmcvfs.translatePath(self.addon.getAddonInfo("path"))
        self.profile = xbmcvfs.translatePath(self.addon.getAddonInfo("profile"))
        self.resources = os.path.join(self.path, "resources")
        self.media = os.path.join(self.resources, "media")
        self.icon = self.addon.getAddonInfo("icon")


    def localize(self, *args):
        if len(args) < 1:
            raise ValueError("String id missing")
        elif len(args) == 1:
            string_id = args[0]
            return self.addon.getLocalizedString(string_id)
        else:
            return [self.addon.getLocalizedString(string_id) for string_id in args]


    def notification(self, message, header=None, time=5000,
                     icon=None, sound=False, show=True):

        if header is None:
            header = self.name

        if icon is None:
            icon = self.icon

        if show:
            xbmcgui.Dialog().notification(header, message, icon, time, sound)


class SettingsHandler():

    def __init__(self, addon):
        self.addon = addon


    def show_settings(self):
        self.addon.openSettings()


    def get_setting(self, setting):
        return self.addon.getSetting(setting).strip()


    def set_setting(self, setting, value):
        self.addon.setSetting(setting, str(value))


    def get_setting_as_bool(self, setting):
        return self.get_setting(setting).lower() == "true"


    def get_setting_as_float(self, setting):
        try:
            return float(self.get_setting(setting))
        except ValueError:
            return 0


    def get_setting_as_int(self, setting):
        try:
            return int(self.get_setting_as_float(setting))
        except ValueError:
            return 0



class FavouritesHandler():
    filename = "favourites.json"


    def __init__(self, profile):
        os.makedirs(profile, exist_ok=True)
        self.save_path = os.path.join(profile, self.filename)
        self.load()


    def load(self):
        try:
            with open(self.save_path, "r") as favourites_file:
                self.favourites_json = json.load(favourites_file)
        except FileNotFoundError:
            self.favourites_json = {}
            self.favourites_json["servers"] = []
            self.save()


    def save(self):
        with open(self.save_path, "w") as favourites_file:
            json.dump(self.favourites_json, favourites_file)


    def get_servers(self):
        return self.favourites_json["servers"]


    def add(self, server):
        servers = self.favourites_json["servers"]
        if server not in servers:
            servers.append(server)
        self.save()


    def remove(self, alias):
        for (id_, server) in enumerate(self.favourites_json["servers"]):
            if server["alias"] == alias:
                del self.favourites_json["servers"][id_]
                break
        self.save()


    def clear(self):
        self.favourites_json["servers"] = []
        self.save()


addon_utils = AddonUtils()
settings_handler = SettingsHandler(addon_utils.addon)
favourites_handler = FavouritesHandler(addon_utils.profile)
