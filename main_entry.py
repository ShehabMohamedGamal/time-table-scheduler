"""
Main Application Entry Point
=============================
Initializes and runs the timetable management system.

Usage:
    python main.py

API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs
"""

import logging
import uvicorn

from config import api_config, db_config
from src.database import DatabaseManager
from src.parser import DataParser
from src.validator import ScheduleValidator
from src.manager import SlotManager
from src.api import APIHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('timetable.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def initialize_application():
    """
    Initialize all application components with dependency injection.
    
    Returns:
        APIHandler instance with configured FastAPI app
    """
    logger.info("Initializing Timetable Management System...")
    
    # Initialize core components
    db_manager = DatabaseManager(db_config.db_path)
    db_manager.initialize_schema()
    logger.info("Database initialized")
    
    parser = DataParser()
    logger.info("Data parser initialized")
    
    validator = ScheduleValidator(db_manager)
    logger.info("Schedule validator initialized")
    
    slot_manager = SlotManager(db_manager, validator)
    logger.info("Slot manager initialized")
    
    api_handler = APIHandler(slot_manager, validator, parser)
    logger.info("API handler initialized")
    
    logger.info("Application initialization complete")
    
    return api_handler


def main():
    """Main application entry point"""
    try:
        # Initialize application
        api_handler = initialize_application()
        
        # Get FastAPI app
        app = api_handler.get_app()
        
        # Run server
        logger.info(f"Starting server on {api_config.host}:{api_config.port}")
        logger.info(f"API documentation available at http://{api_config.host}:{api_config.port}/docs")
        
        uvicorn.run(
            app,
            host=api_config.host,
            port=api_config.port,
            log_level="info"
        )
        
    except Exception as e:
        