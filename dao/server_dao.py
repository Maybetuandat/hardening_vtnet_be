import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Any, Dict, Optional, List, Tuple
from models.server import Server
from schemas.server import ServerCreate, ServerUpdate


class ServerDAO:
    def __init__(self, db: Session):
        self.db = db

    def  count_servers(self) -> int:
        return self.db.query(Server).count()
    def get_active_servers(self, skip : int, limit: int) -> List[Server]:
        return self.db.query(Server).filter(Server.status == True).offset(skip).limit(limit).all()



    def get_all(self, skip: int = 0, limit: int = 10) -> Tuple[List[Server], int]:
        return self.search_servers(skip=skip, limit=limit)

    def get_by_id(self, server_id: int) -> Optional[Server]:
        return self.db.query(Server).filter(Server.id == server_id).first()

    def get_by_hostname(self, hostname: str) -> Optional[Server]:
        return self.db.query(Server).filter(Server.hostname == hostname).first()

    def get_by_ip_address(self, ip_address: str) -> Optional[Server]:
        return self.db.query(Server).filter(Server.ip_address == ip_address).first()

    def search_servers(
        self,
        keyword: Optional[str] = None,
        workload_id: Optional[int] = None,
        status: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Server], int]:
        query = self.db.query(Server)
        
        if keyword and keyword.strip():
            query = query.filter(
                or_(
                    Server.ip_address.ilike(f"%{keyword.strip()}%"),
                    Server.hostname.ilike(f"%{keyword.strip()}%")
                )
            )
        
        # Filter theo status
        if status is not None:
            query = query.filter(Server.status == status)
        
        total = query.count()
        servers = query.offset(skip).limit(limit).all()
        
        return servers, total

    def create(self, server: Server) -> Server:
        try:    
            self.db.add(server)
            self.db.commit()
            self.db.refresh(server)
            return server
            
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, server: Server) -> Server:
        try:
            self.db.commit()
            self.db.refresh(server)
            return server
            
        except IntegrityError as e:
            self.db.rollback()
            if "hostname" in str(e.orig):
                raise ValueError("Hostname đã tồn tại")
            elif "ip_address" in str(e.orig):
                raise ValueError("IP address đã tồn tại")
            else:
                raise ValueError("Dữ liệu không hợp lệ")
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, server_id: int) -> bool:
        try:
            server = self.get_by_id(server_id)
            if not server:
                return False
            
            self.db.delete(server)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e

    # check host name da co loai tru id 
    def check_hostname_exists(self, hostname: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Server).filter(Server.hostname == hostname)
        
        if exclude_id:
            query = query.filter(Server.id != exclude_id)
            
        return query.first() is not None

    # check ip address da co loai tru id 
    def check_ip_exists(self, ip_address: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Server).filter(Server.ip_address == ip_address)
        
        if exclude_id:
            query = query.filter(Server.id != exclude_id)
            
        return query.first() is not None
    

    def count_active_servers(self) -> int:
        """
        Đếm tổng số servers active trong database (để tính pagination)
        """
        return self.db.query(Server).filter(Server.status == True).count()

    def get_servers_batch_for_scan(
        self,
        skip: int,
        limit: int,
        workload_id: Optional[int] = None,
        status: Optional[bool] = None,
        order_by: str = "id"
    ) -> List[Server]:
        """
        Lấy batch servers cho scan với pagination tối ưu
        Sử dụng index trên id để đảm bảo performance tốt với database lớn
        """
        query = self.db.query(Server)
        
        # Filter conditions
        if workload_id is not None:
            query = query.filter(Server.workload_id == workload_id)
            
        if status is not None:
            query = query.filter(Server.status == status)
        
        # Order by ID để đảm bảo consistent pagination
        if order_by == "id":
            query = query.order_by(Server.id)
        elif order_by == "hostname":
            query = query.order_by(Server.hostname)
        elif order_by == "created_at":
            query = query.order_by(Server.created_at)
        else:
            query = query.order_by(Server.id)
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()

    def get_all_servers_paginated(self, skip: int, limit: int) -> Tuple[List[Server], int]:
        """
        Lấy servers với pagination đơn giản (không filter gì)
        Dành cho scan all servers use case
        """
        query = self.db.query(Server).filter(Server.status == True)
        
        total = query.count()
        servers = query.order_by(Server.id).offset(skip).limit(limit).all()
        
        return servers, total

    def get_workload_servers_count(self, workload_id: int) -> int:
        """
        Đếm số servers trong một workload (để estimate scan time)
        """
        return self.db.query(Server).filter(
            Server.workload_id == workload_id,
            Server.status == True
        ).count()

    def get_active_servers_by_os_version(self, os_version: str, skip: int = 0, limit: int = 100) -> Tuple[List[Server], int]:
        """
        Lấy servers theo OS version (để scan theo nhóm OS)
        """
        query = self.db.query(Server).filter(
            Server.os_version == os_version,
            Server.status == True
        )
        
        total = query.count()
        servers = query.order_by(Server.id).offset(skip).limit(limit).all()
        
        return servers, total

    def get_servers_statistics(self) -> Dict[str, Any]:
        """
        Lấy thống kê servers để hiển thị trước khi scan
        """
        try:
            total_servers = self.db.query(Server).count()
            active_servers = self.db.query(Server).filter(Server.status == True).count()
            
            # Group by workload
            workload_stats = self.db.query(
                Server.workload_id,
                func.count(Server.id).label('server_count')
            ).filter(Server.status == True).group_by(Server.workload_id).all()
            
            # Group by OS version  
            os_stats = self.db.query(
                Server.os_version,
                func.count(Server.id).label('server_count')
            ).filter(Server.status == True).group_by(Server.os_version).all()
            
            return {
                "total_servers": total_servers,
                "active_servers": active_servers,
                "inactive_servers": total_servers - active_servers,
                "workload_breakdown": [
                    {"workload_id": w.workload_id, "server_count": w.server_count}
                    for w in workload_stats
                ],
                "os_breakdown": [
                    {"os_version": o.os_version, "server_count": o.server_count}
                    for o in os_stats
                ]
            }
        except Exception as e:
            logging.error(f"Error getting server statistics: {str(e)}")
            return {
                "total_servers": 0,
                "active_servers": 0,
                "inactive_servers": 0,
                "workload_breakdown": [],
                "os_breakdown": []
            }