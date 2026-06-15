=====================
Configuration Module
=====================

.. currentmodule:: tet.config

The configuration module provides Tet's application factory pattern and enhanced configurator functionality.

Application Factory
===================

.. autofunction:: application_factory

   The main decorator for creating Tet applications. This decorator automatically configures
   Tet features and creates a WSGI application from your configuration function.

   Example usage::

       from tet.config import application_factory, ALL_FEATURES

       @application_factory(included_features=ALL_FEATURES)
       def main(config):
           config.add_route('home', '/')
           config.scan()

Configurator Factory
====================

.. autofunction:: create_configurator

   Creates a Pyramid configurator with Tet features automatically configured.

   Example usage::

       from tet.config import create_configurator

       def main(global_config, **settings):
           config = create_configurator(
               global_config=global_config,
               settings=settings,
               included_features=['renderers.json', 'security.csrf']
           )
           return config.make_wsgi_app()

Feature Constants
================

.. autodata:: ALL_FEATURES

   List of all available Tet features:

   * ``"services"`` - Service configuration
   * ``"i18n"`` - Internationalization support  
   * ``"renderers.json"`` - Enhanced JSON renderer
   * ``"renderers.tonnikala"`` - Tonnikala template renderer
   * ``"renderers.tonnikala.i18n"`` - Tonnikala with i18n
   * ``"security.authorization"`` - Enhanced authorization
   * ``"security.csrf"`` - CSRF protection

.. autodata:: MINIMAL_FEATURES

   Empty list for applications that want to manually configure all features.

Legacy Application Factory
==========================

.. autoclass:: TetAppFactory
   :members:
   :show-inheritance:

   .. deprecated:: 
      This class is deprecated in favor of the ``@application_factory`` decorator.
      Use the decorator-based approach for new applications.