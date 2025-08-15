from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.command_schemas import CommandCreate, CommandResponse, CommandUpdate, CommandWithRuleResponse
from services.command_service import CommandService

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/commands", tags=["Commands"])


@router.get("", response_model=List[CommandWithRuleResponse])
async def get_all_commands(
    rule_id: int = Query(None, description="Filter by rule ID"),
    os_version: str = Query(None, description="Filter by OS version"),
    active_only: bool = Query(False, description="Get only active commands"),
    db: Session = Depends(get_db)
):
    """Get all commands with optional filtering"""
    try:
        if active_only:
            commands = CommandService.get_active_commands(db)
        elif rule_id and os_version:
            # For rule and OS filter, use the basic response
            basic_commands = CommandService.get_commands_by_rule_and_os(db, rule_id, os_version)
            # Convert to response with rule info
            commands = []
            for command_response in basic_commands:
                full_command = CommandService.get_command_by_id(db, command_response.id)
                if full_command:
                    commands.append(full_command)
        elif rule_id:
            # For rule filter, use the basic response
            basic_commands = CommandService.get_commands_by_rule(db, rule_id)
            # Convert to response with rule info
            commands = []
            for command_response in basic_commands:
                full_command = CommandService.get_command_by_id(db, command_response.id)
                if full_command:
                    commands.append(full_command)
        elif os_version:
            commands = CommandService.get_commands_by_os(db, os_version)
        else:
            commands = CommandService.get_all_commands(db)
        
        return commands
    except Exception as e:
        logger.error(f"Error fetching commands: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commands: {str(e)}"
        )


@router.get("/{command_id}", response_model=CommandWithRuleResponse)
async def get_command(command_id: int, db: Session = Depends(get_db)):
    """Get command by ID"""
    try:
        command = CommandService.get_command_by_id(db, command_id)
        if not command:
            logger.warning(f"Command with ID {command_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Command not found"
            )
        return command
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch command: {str(e)}"
        )


@router.post("", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def create_command(command_data: CommandCreate, db: Session = Depends(get_db)):
    """Create a new command"""
    try:
        command = CommandService.create_command(db, command_data)
        logger.info(f"Command created successfully for rule: {command.rule_id}")
        return command
    except ValueError as e:
        logger.error(f"Validation error creating command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create command: {str(e)}"
        )


@router.put("/{command_id}", response_model=CommandResponse)
async def update_command(
    command_id: int, 
    command_data: CommandUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing command"""
    try:
        updated_command = CommandService.update_command(db, command_id, command_data)
        if not updated_command:
            logger.warning(f"Command with ID {command_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Command not found"
            )
        logger.info(f"Command with ID {command_id} updated successfully")
        return updated_command
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update command: {str(e)}"
        )


@router.delete("/{command_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_command(command_id: int, db: Session = Depends(get_db)):
    """Delete a command"""
    try:
        success = CommandService.delete_command(db, command_id)
        if not success:
            logger.warning(f"Command with ID {command_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Command not found"
            )
        logger.info(f"Command with ID {command_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete command: {str(e)}"
        )


@router.get("/rule/{rule_id}", response_model=List[CommandResponse])
async def get_commands_by_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get all commands for a specific rule"""
    try:
        commands = CommandService.get_commands_by_rule(db, rule_id)
        return commands
    except Exception as e:
        logger.error(f"Error fetching commands by rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commands by rule: {str(e)}"
        )


@router.get("/rule/{rule_id}/count")
async def get_commands_count_by_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get number of commands for a specific rule"""
    try:
        from dao.command_dao import CommandDAO
        count = CommandDAO.get_commands_count_by_rule(db, rule_id)
        logger.info(f"Number of commands for rule {rule_id}: {count}")
        return {"count": count}
    except Exception as e:
        logger.error(f"Error fetching commands count by rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commands count by rule: {str(e)}"
        )


@router.get("/os/{os_version}", response_model=List[CommandWithRuleResponse])
async def get_commands_by_os(os_version: str, db: Session = Depends(get_db)):
    """Get all commands for a specific OS version"""
    try:
        commands = CommandService.get_commands_by_os(db, os_version)
        return commands
    except Exception as e:
        logger.error(f"Error fetching commands by OS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commands by OS: {str(e)}"
        )


@router.get("/os/{os_version}/count")
async def get_commands_count_by_os(os_version: str, db: Session = Depends(get_db)):
    """Get number of commands for a specific OS version"""
    try:
        from dao.command_dao import CommandDAO
        count = CommandDAO.get_commands_count_by_os(db, os_version)
        logger.info(f"Number of commands for OS {os_version}: {count}")
        return {"count": count}
    except Exception as e:
        logger.error(f"Error fetching commands count by OS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commands count by OS: {str(e)}"
        )


@router.get("/rule/{rule_id}/os/{os_version}", response_model=List[CommandResponse])
async def get_commands_by_rule_and_os(rule_id: int, os_version: str, db: Session = Depends(get_db)):
    """Get commands for a specific rule and OS version"""
    try:
        commands = CommandService.get_commands_by_rule_and_os(db, rule_id, os_version)
        return commands
    except Exception as e:
        logger.error(f"Error fetching commands by rule and OS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commands by rule and OS: {str(e)}"
        )