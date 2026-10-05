import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from .config import Settings

_config = Settings.get_config(strict=False)
_logger = logging.getLogger(_config.logging_default_logger_name)


def construct_db_datasource(db_driver, db_username, db_password, db_hostname, db_port, db_dbname) -> str:
    datasource = ""
    if db_driver:
        datasource += f"{db_driver}://"
    if db_username:
        datasource += f"{db_username}:{db_password}@"
    if db_hostname:
        datasource += db_hostname
    if db_port:
        datasource += f":{db_port}"
    if db_dbname:
        datasource += f"/{db_dbname}"
    _logger.debug("Constructed database datasource: %s", datasource)
    return datasource


def get_engine():
    """
    Returns a dictionary containing database engines for different databases.
    - db_engine_master_data: Engine for master-data-db (IncomingPartner, etc.)
    """
    db_datasource_master_data = construct_db_datasource(
        _config.master_data_db_driver,
        _config.master_data_db_username,
        _config.master_data_db_password,
        _config.master_data_db_hostname,
        _config.master_data_db_port,
        _config.master_data_db_dbname,
    )
    db_engine_master_data = create_async_engine(db_datasource_master_data, poolclass=NullPool)

    return {
        "db_engine_master_data": db_engine_master_data,
    }


# Singleton instance
_engines = None


def get_engines():
    global _engines
    if _engines is None:
        _engines = get_engine()
    return _engines

