from typing import Optional, List
from sqlalchemy.orm import Session
from models.command import Command
from schemas.command_schemas import CommandCreate, CommandUpdate


class CommandDAO:
    
    @staticmethod
    def get_all_commands(db: Session) -> List[Command]:
        """Get all commands"""
        return db.query(Command).all()
    
    @staticmethod
    def get_command_by_id(db: Session, command_id: int) -> Optional[Command]:
        """Get command by ID"""
        return db.query(Command).filter(Command.id == command_id).first()
    
    @staticmethod
    def get_commands_by_rule(db: Session, rule_id: int) -> List[Command]:
        """Get commands by rule ID"""
        return db.query(Command).filter(
            Command.rule_id == rule_id,
            Command.is_active == True
        ).all()
    
    @staticmethod
    def get_commands_by_rule_and_os(db: Session, rule_id: int, os_version: str) -> List[Command]:
        """Get commands by rule ID and OS version"""
        return db.query(Command).filter(
            Command.rule_id == rule_id,
            Command.os_version == os_version,
            Command.is_active == True
        ).all()
    
    @staticmethod
    def get_commands_by_os(db: Session, os_version: str) -> List[Command]:
        """Get commands by OS version"""
        return db.query(Command).filter(
            Command.os_version == os_version,
            Command.is_active == True
        ).all()
    
    @staticmethod
    def get_active_commands(db: Session) -> List[Command]:
        """Get all active commands"""
        return db.query(Command).filter(Command.is_active == True).all()
    
    @staticmethod
    def create_command(db: Session, command_data: CommandCreate) -> Command:
        """Create a new command"""
        db_command = Command(
            rule_id=command_data.rule_id,
            os_version=command_data.os_version,
            command_text=command_data.command_text,
            is_active=command_data.is_active
        )
        db.add(db_command)
        db.commit()
        db.refresh(db_command)
        return db_command
    
    @staticmethod
    def update_command(db: Session, command_id: int, command_data: CommandUpdate) -> Optional[Command]:
        """Update an existing command"""
        db_command = db.query(Command).filter(Command.id == command_id).first()
        if not db_command:
            return None

        # Update only provided fields
        update_data = command_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_command, field, value)

        db.commit()
        db.refresh(db_command)
        return db_command
    
    @staticmethod
    def delete_command(db: Session, command_id: int) -> bool:
        """Delete a command"""
        db_command = db.query(Command).filter(Command.id == command_id).first()
        if not db_command:
            return False

        db.delete(db_command)
        db.commit()
        return True
    
    @staticmethod
    def get_commands_count_by_rule(db: Session, rule_id: int) -> int:
        """Get count of commands for a rule"""
        return db.query(Command).filter(
            Command.rule_id == rule_id,
            Command.is_active == True
        ).count()
    
    @staticmethod
    def get_commands_count_by_os(db: Session, os_version: str) -> int:
        """Get count of commands for an OS version"""
        return db.query(Command).filter(
            Command.os_version == os_version,
            Command.is_active == True
        ).count()