from typing import Optional, List
from sqlalchemy.orm import Session
from models.command import Command


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