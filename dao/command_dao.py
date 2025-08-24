from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from models.command import Command
class CommandDAO: 
    def __init__(self, db : Session):
        self.db = db 
    def get_all(self):
        return self.db.query(Command).all()
    


    def get_by_rule_id_and_os_version(self, rule_id: int, os_version: str) -> Command:
        print("DEBUG get_by_rule_id_and_os_version:", rule_id, os_version)
        
        
        commands = (
            self.db.query(Command)
            .filter(Command.rule_id == rule_id)
            .all()
        )
        
        
        target_os = os_version.strip().lower()
        for cmd in commands:
            cmd_os = cmd.os_version.strip().lower() if cmd.os_version else ""
            print(f"DEBUG: Comparing '{cmd_os}' with '{target_os}'")
            if cmd_os == target_os:
                print(f"DEBUG: Found matching command: {cmd.id}")
                return cmd
        
        print("DEBUG: No matching command found")
        return None
    def get_by_id(self, command_id: int) -> Optional[Command]:
        return self.db.query(Command).filter(Command.id == command_id).first()
    
    def get_by_os_version(self, os_version: str) -> List[Command]:
        return self.db.query(Command).filter(Command.os_version == os_version).all()
    def get_by_rule_id(self, rule_id: int) -> List[Command]:
        return self.db.query(Command).filter(Command.rule_id == rule_id).all()
    


    def create(self, command: Command) -> Command:
        try:
            self.db.add(command)
            self.db.commit()
            self.db.refresh(command)
            return command
        except IntegrityError as e:
            self.db.rollback()
            raise e
    
    def update(self, command: Command) -> Command:
        try:
            self.db.commit()
            self.db.refresh(command)
            return command
        except IntegrityError as e:
            self.db.rollback()
            raise e
    
    def delete(self, command: Command) -> None:
        try:
            self.db.delete(command)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e