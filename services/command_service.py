from sqlalchemy.orm import Session
from typing import Optional, List
from dao import command_dao
from dao.command_dao import CommandDAO
from models.command import Command
from schemas.command import CommandCreate, CommandUpdate, CommandResponse

class CommandService:
    def __init__(self, db: Session):
        self.command_dao = CommandDAO(db)
    
    # function nay co the khong dung den 
    def get_all_commands(self) -> List[CommandResponse]:
        commands = self.command_dao.get_all()
        return [self._convert_to_response(command) for command in commands]
    
    
    def get_command_by_id(self, command_id: int) -> Optional[CommandResponse]:
        if command_id <= 0:
            return None
        command = self.command_dao.get_by_id(command_id)
        if command:
            return self._convert_to_response(command)
        return None
    
    def get_commands_by_os_version(self, os_version: str) -> List[CommandResponse]:
        if not os_version or not os_version.strip():
            return []
        commands = self.command_dao.get_by_os_version(os_version.strip().lower())
        return [self._convert_to_response(command) for command in commands]
    
    def get_commands_by_rule_id(self, rule_id: int) -> List[CommandResponse]:
        if rule_id <= 0:
            return []
        commands = self.command_dao.get_by_rule_id(rule_id)
        return [self._convert_to_response(command) for command in commands]
    
    def get_command_for_rule_excecution(self, rule_id: int, os_version: str) -> Command:
        if rule_id <= 0 or not os_version or not os_version.strip():
            return None
        command = self.command_dao.get_command_active_by_rule_id_and_os_version(rule_id, os_version.strip().lower())
        if command:
            return command
        
        return None
    def create_command(self, command_data: CommandCreate) -> CommandResponse:
        try:
            self._validate_command_create_data(command_data)
            
            command_dict = command_data.dict(exclude_none=True)
            command_model = Command(**command_dict)
            
            created_command = self.command_dao.create(command_model)
            return self._convert_to_response(created_command)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo command: {str(e)}")
    
    def update_command(self, command_id: int, command_data: CommandUpdate) -> Optional[CommandResponse]:
        try:
            if command_id <= 0:
                return None
                
            existing_command = self.command_dao.get_by_id(command_id)
            if not existing_command:
                return None
                
            self._validate_command_update_data(command_data)
            
            update_data = command_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(existing_command, field) and value is not None:
                    setattr(existing_command, field, value)
            
            updated_command = self.command_dao.update(existing_command)
            return self._convert_to_response(updated_command)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi cập nhật command: {str(e)}")
    
    def delete_command(self, command_id: int) -> bool:
        try:
            if command_id <= 0:
                return False
                
            existing_command = self.command_dao.get_by_id(command_id)
            if not existing_command:
                return False
            
            self.command_dao.delete(existing_command)
            return True
            
        except Exception as e:
            raise Exception(f"Lỗi khi xóa command: {str(e)}")
    
    def _convert_to_response(self, command: Command) -> CommandResponse:
        return CommandResponse(
            id=command.id,
            rule_id=command.rule_id,
            os_version=command.os_version,
            command_text=command.command_text,
            is_active=command.is_active,
            created_at=command.created_at,
            updated_at=command.updated_at
        )
    
    def _validate_command_create_data(self, command_data: CommandCreate) -> None:
        if not command_data.os_version or not command_data.os_version.strip():
            raise ValueError("OS version không được để trống")
            
        if not command_data.command_text or not command_data.command_text.strip():
            raise ValueError("Command text không được để trống")
            
        if command_data.rule_id <= 0:
            raise ValueError("Rule ID phải lớn hơn 0")
    
    def _validate_command_update_data(self, command_data: CommandUpdate) -> None:
        if command_data.os_version is not None and (not command_data.os_version or not command_data.os_version.strip()):
            raise ValueError("OS version không được để trống")
            
        if command_data.command_text is not None and (not command_data.command_text or not command_data.command_text.strip()):
            raise ValueError("Command text không được để trống")
            
        if command_data.rule_id is not None and command_data.rule_id <= 0:
            raise ValueError("Rule ID phải lớn hơn 0")