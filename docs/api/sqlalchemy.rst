===================
SQLAlchemy Modules
===================

.. currentmodule:: tet.sqlalchemy

Root Factory
============

.. automodule:: tet.sqlalchemy.factory
   :members:
   :undoc-members:
   :show-inheritance:

   .. autoclass:: SQLARootFactory
      :members:
      :special-members: __init__, __getitem__

Simple SQLAlchemy Integration
=============================

.. automodule:: tet.sqlalchemy.simple
   :members:
   :undoc-members:
   :show-inheritance:

   Key Functions
   -------------

   .. autofunction:: declarative_base

   .. autofunction:: get_tm_session

   .. autofunction:: setup_sqlalchemy

   Configuration Directive
   ----------------------

   The ``setup_sqlalchemy`` function is added as a configuration directive when you include
   ``tet.sqlalchemy.simple``. It automatically configures:

   - **pyramid_di**: Service registration for database sessions  
   - **pyramid_tm**: Transaction management middleware
   - **Request-scoped sessions**: Sessions tied to request lifecycle
   - **Automatic cleanup**: Sessions closed after request completion

   Example usage::

       @application_factory(included_features=ALL_FEATURES)
       def main(config):
           config.include('tet.sqlalchemy.simple')
           config.setup_sqlalchemy()  # Configure everything automatically

Password Utilities
==================

.. automodule:: tet.sqlalchemy.password
   :members:
   :undoc-members:
   :show-inheritance: