from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from dao.command_dao import CommandDAO
from dao.rule_dao import RuleDAO
from models.command import Command
from schemas.command_schemas import CommandCreate, CommandUpdate, CommandResponse, CommandWithRuleResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class CommandService:
    """Service layer for Command operations"""

    @staticmethod
    def get_all_commands(db: Session) -> List[CommandWithRuleResponse]:
        """Get all commands with rule information"""
        try:
            logger.info("Fetching all commands from database")
            commands = CommandDAO.get_all_commands(db)
            logger.info(f"Found {len(commands)} commands")
            return [CommandService._to_response_with_rule(db, command) for command in commands]
        except Exception as e:
            logger.error(f"Error fetching commands: {str(e)}")
            raise

    @staticmethod
    def get_command_by_id(db: Session, command_id: int) -> Optional[CommandWithRuleResponse]:
        """Get command by ID with rule information"""
        try:
            logger.info(f"Fetching command with ID: {command_id}")
            command = CommandDAO.get_command_by_id(db, command_id)
            if command:
                logger.info(f"Found command for rule: {command.rule_id}")
                return CommandService._to_response_with_rule(db, command)
            else:
                logger.warning(f"Command with ID {command_id} not found")
                return None
        except Exception as e:
            logger.error(f"Error fetching command: {str(e)}")
            raise

    @staticmethod
    def create_command(db: Session, command_data: CommandCreate) -> CommandResponse:
        """Create a new command"""
        try:
            logger.info(f"Creating new command for rule ID: {command_data.rule_id}")
            
            # Validate rule exists
            rule = RuleDAO.get_rule_by_id(db, command_data.rule_id)
            if not rule:
                raise ValueError(f"Rule with ID {command_data.rule_id} does not exist")
            
            command = CommandDAO.create_command(db, command_data)
            logger.info(f"Command created successfully for rule: {command.rule_id}")
            return CommandService._to_response(command)
        except ValueError as e:
            logger.error(f"Validation error creating command: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating command: {str(e)}")
            raise

    @staticmethod
    def update_command(db: Session, command_id: int, command_data: CommandUpdate) -> Optional[CommandResponse]:
        """Update an existing command"""
        try:
            logger.info(f"Updating command with ID: {command_id}")
            
            # Check if command exists
            existing_command = CommandDAO.get_command_by_id(db, command_id)
            if not existing_command:
                logger.warning(f"Command with ID {command_id} not found for update")
                return None
            
            # Validate rule exists (if being updated)
            if command_data.rule_id:
                rule = RuleDAO.get_rule_by_id(db, command_data.rule_id)
                if not rule:
                    raise ValueError(f"Rule with ID {command_data.rule_id} does not exist")
            
            updated_command = CommandDAO.update_command(db, command_id, command_data)
            if updated_command:
                logger.info(f"Command updated successfully: {updated_command.id}")
                return CommandService._to_response(updated_command)
            return None
        except ValueError as e:
            logger.error(f"Validation error updating command: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating command: {str(e)}")
            raise

    @staticmethod
    def delete_command(db: Session, command_id: int) -> bool:
        """Delete a command"""
        try:
            logger.info(f"Deleting command with ID: {command_id}")
            
            # Check if command exists
            existing_command = CommandDAO.get_command_by_id(db, command_id)
            if not existing_command:
                logger.warning(f"Command with ID {command_id} not found for deletion")
                return False
            
            success = CommandDAO.delete_command(db, command_id)
            if success:
                logger.info(f"Command with ID {command_id} deleted successfully")
            return success
        except Exception as e:
            logger.error(f"Error deleting command: {str(e)}")
            raise

    @staticmethod
    def get_commands_by_rule(db: Session, rule_id: int) -> List[CommandResponse]:
        """Get commands by rule ID"""
        try:
            logger.info(f"Fetching commands for rule: {rule_id}")
            commands = CommandDAO.get_commands_by_rule(db, rule_id)
            logger.info(f"Found {len(commands)} commands for rule {rule_id}")
            return [CommandService._to_response(command) for command in commands]
        except Exception as e:
            logger.error(f"Error fetching commands by rule: {str(e)}")
            raise

    @staticmethod
    def get_commands_by_rule_and_os(db: Session, rule_id: int, os_version: str) -> List[CommandResponse]:
        """Get commands by rule ID and OS version"""
        try:
            logger.info(f"Fetching commands for rule {rule_id} and OS {os_version}")
            commands = CommandDAO.get_commands_by_rule_and_os(db, rule_id, os_version)
            logger.info(f"Found {len(commands)} commands for rule {rule_id} and OS {os_version}")
            return [CommandService._to_response(command) for command in commands]
        except Exception as e:
            logger.error(f"Error fetching commands by rule and OS: {str(e)}")
            raise

    @staticmethod
    def get_commands_by_os(db: Session, os_version: str) -> List[CommandWithRuleResponse]:
        """Get commands by OS version"""
        try:
            logger.info(f"Fetching commands for OS: {os_version}")
            commands = CommandDAO.get_commands_by_os(db, os_version)
            logger.info(f"Found {len(commands)} commands for OS {os_version}")
            return [CommandService._to_response_with_rule(db, command) for command in commands]
        except Exception as e:
            logger.error(f"Error fetching commands by OS: {str(e)}")
            raise

    @staticmethod
    def get_active_commands(db: Session) -> List[CommandWithRuleResponse]:
        """Get only active commands"""
        try:
            logger.info("Fetching active commands")
            commands = CommandDAO.get_active_commands(db)
            logger.info(f"Found {len(commands)} active commands")
            return [CommandService._to_response_with_rule(db, command) for command in commands]
        except Exception as e:
            logger.error(f"Error fetching active commands: {str(e)}")
            raise

    @staticmethod
    def _to_response(command: Command) -> CommandResponse:
        """Convert Command model to CommandResponse"""
        return CommandResponse(
            id=command.id,
            rule_id=command.rule_id,
            os_version=command.os_version,
            command_text=command.command_text,
            is_active=command.is_active,
            created_at=command.created_at,
            updated_at=command.updated_at
        )

    @staticmethod
    def _to_response_with_rule(db: Session, command: Command) -> CommandWithRuleResponse:
        """Convert Command model to CommandWithRuleResponse"""
        rule = RuleDAO.get_rule_by_id(db, command.rule_id)
        
        return CommandWithRuleResponse(
            id=command.id,
            rule_id=command.rule_id,
            rule_name=rule.name if rule else None,
            rule_severity=rule.severity if rule else None,
            os_version=command.os_version,
            command_text=command.command_text,
            is_active=command.is_active,
            created_at=command.created_at,
            updated_at=command.updated_at
        )