# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.pluginmanager
# User plugin platform to extend pyCrossword functionality based on [Yapsy](http://yapsy.sourceforge.net/).
# @see [example 1](http://yapsy.sourceforge.net/FilteredPluginManager.html), 
# [example 2](https://stackoverflow.com/questions/5333128/yapsy-minimal-example)
from yapsy.PluginManager import PluginManager
from PyQt5 import QtWidgets
from .globalvars import *

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Wrapper class for the application main window (pycross::gui::MainWindow).
# Adds a few convenience methods to call the main app actions, query and set global settings, etc.
# TODO: Must think of a more protected way to expose the main window's methods and members.
class PxAPI:

    ## Constructor takes a single parameter - the instance of pycross::gui::MainWindow (main window).
    def __init__(self, mainwindow):
        ## `pycross::gui::MainWindow` internal pointer to app main window instance
        self.__mainwindow = mainwindow        
        # iterate and add 'safe' methods to this wrapper class
        for objname in dir(self.__mainwindow):
            obj = getattr(self.__mainwindow, objname)
            if callable(obj) and not objname.startswith('_'):
                setattr(self, objname, obj)
        
    ## Triggers an action of the app main window.
    # @param action_name `str` object name or display text of the action to be called
    # @param display_name `bool` True if the display text is passed, otherwise, the action will be
    # located by its object (variable) name
    def trigger_action(self, action_name, display_name=True):
        actn = None
        if not display_name:
            actn = self.get_prop(action_name)
            if not actn or not isinstance(actn, QtWidgets.QAction):
                raise AttributeError(_("MainWindow has no '{}' action!").format(action_name))            
            actn.trigger()
        else:
            for objname in dir(self.__mainwindow):
                actn = self.get_prop(objname)
                if actn and isinstance(actn, QtWidgets.QAction) and (actn.text() == action_name):
                    actn.trigger()
                    break
            else:
                raise AttributeError(_("MainWindow has no '{}' action!").format(action_name))

    ## Sets a global option value.
    # @param option `str` an option search string delimited by 'option_sep', e.g. 'plugins/thirdparty/git/active'
    # @param value value written to the option
    # @param option_sep `str` the option key string delimiter (default = '/')
    # @param apply `bool` if True, the new settings will be applied straightforward
    # @param save_settings `bool` if True, the settings file will be updated (saved)
    def set_option(self, option, value, option_sep='/', apply=True, save_settings=True):
        keys = option.split(option_sep)
        op = self.__mainwindow.options()
        for key in keys:
            op = op[key]
        op = value
        if apply: self.__mainwindow.apply_config(save_settings, False)

    ## Gets a global option value or the whole global settings dictionary.
    # @param option `str`|`None` an option search string delimited by 'option_sep', 
    # e.g. 'plugins/thirdparty/git/active'. If `None`, the whole 
    # guisettings::CWSettings::settings dictionary is returned.
    # @param option_sep `str` the option key string delimiter (default = '/')
    # @returns value of the located option
    # @exception `KeyError` unable to locate option in guisettings::CWSettings::settings
    def get_option(self, option=None, option_sep='/'):       
        op = self.__mainwindow.options()
        if not option: return op
        keys = option.split(option_sep)
        for key in keys:
            op = op[key]
        return op

    ## Getter method for the main window members by their name.
    # @param propname `str` member name (property or method)
    # @param default the default value if the member wasn't found (default = `None`)
    def get_prop(self, propname, default=None):
        return getattr(self.__mainwindow, propname, default)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Reimplemented PluginManager class to enable plugins' access to the main window.
class PxPluginManager(PluginManager):

    ## Adds 'mainwindow' to the PluginManager default constructor.
    # @param mainwindow `pycross.gui.MainWindow` pointer to the app main window
    # @param categories_filter `dict` categories of plugins to be looked for as well as the way to recognise them
    # @param directories_list `iterable` list of search directories for plugins (relative or absolute paths)
    # @param plugin_info_ext `str` extension of plugin info files (without dot)
    # @param plugin_locator `yapsy::IPluginLocator::IPluginLocator` plugin locator instance
    def __init__(self, mainwindow, categories_filter=None, directories_list=None, plugin_info_ext=None, plugin_locator=None):
        super().__init__(categories_filter, directories_list, plugin_info_ext, plugin_locator)
        ## `PxAPI` wrapper instance for app main window
        #self.__mainwindow = mainwindow
        self.mainwin = PxAPI(mainwindow)

    ## Reimplemented method that creates plugin objects passing 'self' in constructor.
    # See params in yapsy docs.
    def instanciateElementWithImportInfo(self, element, element_name, plugin_module_name, candidate_filepath):
        return element(self)

    ## Calls a given method from a given plugin by its name.
    # @param plugin_name `str` name of plugin
    # @param plugin_category `str` name of plugin category 
    # @param method_name `str` name of method to call
    # @param *args `positional args` positional args passed to the method
    # @param *kwargs `keyword args` keyword args passed to the method
    # @returns whatever the called method returns
    # @exception `Exception` failure to locate plugin or plugin inactive or failure to locate method
    def call_plugin_method(self, plugin_name, plugin_category, method_name, *args, **kwargs):
        plugin = self.getPluginByName(plugin_name, plugin_category)
        if plugin is None:
            raise Exception(_("Unable to locate plugin '{}' in category '{}'!").format(plugin_name, plugin_category))
        if not plugin.is_activated:
            raise Exception(_("Plugin '{}' is not active. Cannot call method of inactive plugin!").format(plugin_name))
        meth = getattr(plugin.plugin_object, method_name, None)
        if meth is None or not callable(meth):
            raise Exception(_("Unable to locate method '{}' in plugin '{}'!").format(method_name, plugin_name))
        return meth(*args, **kwargs)

    ## @brief Makes a dictionary of plugin info given a plugin object.
    # The resulting dict is formatted in the same way as in the global settings,
    # corresponding to a custom plugin record in a given category.
    # @param plugin `yapsy::PluginInfo::PluginInfo` the plugin object
    # @returns `dict` plugin info record
    def _plugin_info_to_dic(self, plugin):
        return {'name': plugin.name, 'active': plugin.is_activated, 'author': plugin.author, 
                'copyright': plugin.copyright, 'description': plugin.description,
                'path': plugin.path, 'version': str(plugin.version), 'website': plugin.website}

    ## Returns the plugin object corresponding to a plugin info record in the global settings.
    # @param settings `dict` pointer to global settings
    # @param plugin_name `str` name of plugin
    # @param plugin_category `str` name of plugin category
    # @returns `yapsy::PluginInfo::PluginInfo` plugin object or `None` on failure
    def _plugin_from_settings(self, settings, plugin_name, plugin_category):
        if not plugin_category in settings:
            return None
        for plugin_info in settings[plugin_category]:
            if plugin_info['name'] == plugin_name:
                return self.getPluginByName(plugin_name, plugin_category)
        return None

    ## Sets a plugin's active state to True or False.
    # @param plugin_name `str` name of plugin
    # @param plugin_category `str` name of plugin category
    # @param active `bool` active state to set
    def set_plugin_active(self, plugin_name, plugin_category, active=True):
        if active:
            self.activatePluginByName(plugin_name, plugin_category)
        else:
            self.deactivatePluginByName(plugin_name, plugin_category)

    ## @brief Updates the custom plugin settings in guisettings::CWSettings::settings.
    # The function will first look for plugins contained in the current settings
    # and update their data from the existing plugins collected by the plugin manager.
    # Plugins that are found in settings but not in the plugin manager will be removed from settings.
    # Then finally plugins collected by the manager but not contained in the settings
    # will be appended to the settings, in their respective categories.
    # @param forced_update `bool` if `True`, all current plugin settings will be cleared
    # and plugins will be added anew from the plugin manager (default = `False`)
    def update_global_settings(self, forced_update=False):
        settings = self.mainwin.get_option('plugins/custom')
        
        for category in settings:

            if forced_update: 
                settings[category].clear()

            # Step 1 - update existing plugins, delete non-existing
            i = 0
            # iterate settings plugins in category
            while i < len(settings[category]):
                # find actual plugin
                plugin = self.getPluginByName(settings[category][i]['name'], category)
                if plugin is None:
                    # if non-existing, remove from settings
                    del settings[category][i]
                else:
                    # if existing, active / deactivate it based on current settings
                    self.set_plugin_active(settings[category][i]['name'], category, settings[category][i]['active'])                    
                    # update plugin info in settings
                    settings[category][i].update(self._plugin_info_to_dic(plugin))
                    i += 1

            # Step 2 - add new plugins in deactivated state
            for pl in self.getPluginsOfCategory(category):
                # iterate settings plugins in category
                for plugin_info in settings[category]:
                    # break from loop if plugin already there
                    if plugin_info['name'] == pl.name:
                        break
                else:
                    # if not found in settings, append new plugin at the end
                    settings[category].append(self._plugin_info_to_dic(pl))

        if DEBUGGING: print(settings)

    ## @brief Gets the list of plugins for a given category respecting their order.
    # This method is added since the inherited `getPluginsOfCategory` method of `PluginManager`
    # does not respect the order of the plugins (it knows nothing about the order).
    # The plugin order is taken from the global settings (guisettings::CWSettings::settings).
    # @param category `str` plugin category name
    # @param active_only `bool` only list active plugins (default)
    # @returns `list` list of plugins of type yapsy::PluginInfo::PluginInfo
    def get_plugins_of_category(self, category, active_only=True):
        plugins = []
        settings = self.mainwin.get_option('plugins/custom')
        for pl in settings[category]:
            if not active_only or pl['active']:
                plugin = self.getPluginByName(pl['name'], category)
                if not plugin is None: 
                    plugins.append(plugin)
        return plugins

    ## @brief Returns the list of methods with a given name from all active plugins.
    # The methods are returned from all active plugins in a given category,
    # while respecting the plugin order in the global settings. That is,
    # the resulting list of methods will be ordered by the plugin order in the settings.
    # @param category `str` plugin category name
    # @param method_name `str` method name to look for
    # @returns `list` list of methods, each being a callable bound object
    def get_plugin_methods(self, category, method_name):
        methods = []
        for plugin in self.get_plugins_of_category(category):
            m = getattr(plugin.plugin_object, method_name, None)
            if m and callable(m):
                methods.append(m)
        #if DEBUGGING: print(f"FOUND METHODS: {methods}")
        return methods

    ## Activates or deactivates loaded plugins according to the global settings.
    def configure_plugins(self):
        settings = self.mainwin.get_option('plugins/custom')
        for cat_name in settings:
            for plugin in settings[cat_name]:                
                self.set_plugin_active(plugin['name'], cat_name, plugin['active'])