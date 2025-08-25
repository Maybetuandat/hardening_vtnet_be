from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.command import CommandCreate, CommandResponse, CommandUpdate
from services.command_service import CommandService


router = APIRouter(prefix="/api/commands", tags=["Commands"])
def get_command_service(db : Session = Depends(get_db)) -> CommandService:
    return CommandService(db)

@router.get("/{rule_id}", response_model=List[CommandResponse])
async def get_commands_with_rule_id(rule_id: int, command_service: CommandService = Depends(get_command_service)) -> List[CommandResponse]:
    return command_service.get_commands_by_rule_id(rule_id)



@router.post("/", response_model=CommandResponse)
async def create_command(command_data: CommandCreate, command_service: CommandService = Depends(get_command_service)) -> CommandResponse:
    return command_service.create_command(command_data)


@router.put("/{command_id}", response_model=CommandResponse)
async def update_command(command_id: int, command_data: CommandUpdate, command_service: CommandService = Depends(get_command_service)) -> CommandResponse:
    return command_service.update_command(command_id, command_data)
@router.delete("/{command_id}", response_model=None)
async def delete_command(command_id: int, command_service: CommandService = Depends(get_command_service)) -> None:
    command_service.delete_command(command_id)
    return {
        "success": True,
        "message": "Command deleted successfully"
    }