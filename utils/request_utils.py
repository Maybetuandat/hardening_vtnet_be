# utils/request_utils.py
from typing import Optional
from fastapi import Request

def get_client_ip(request: Request) -> Optional[str]:
    """
    Lấy IP address từ request
    Ưu tiên X-Forwarded-For header trước, sau đó fallback về client host
    """
    try:
        # Kiểm tra X-Forwarded-For header (cho proxy/load balancer)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Lấy IP đầu tiên trong danh sách (IP gốc của client)
            return forwarded.split(",")[0].strip()
        
        # Kiểm tra X-Real-IP header (cho một số proxy configs)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback về client host
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return None
    except Exception:
        return None

def get_user_agent(request: Request) -> Optional[str]:
    """
    Lấy User Agent từ request headers
    """
    try:
        return request.headers.get("user-agent")
    except Exception:
        return None

def get_request_method(request: Request) -> Optional[str]:
    """
    Lấy HTTP method từ request
    """
    try:
        return request.method
    except Exception:
        return None

def get_request_url(request: Request) -> Optional[str]:
    """
    Lấy full URL từ request
    """
    try:
        return str(request.url)
    except Exception:
        return None

def get_request_path(request: Request) -> Optional[str]:
    """
    Lấy path từ request (không bao gồm query parameters)
    """
    try:
        return request.url.path
    except Exception:
        return None

def get_referer(request: Request) -> Optional[str]:
    """
    Lấy Referer header từ request
    """
    try:
        return request.headers.get("referer")
    except Exception:
        return None

def get_content_type(request: Request) -> Optional[str]:
    """
    Lấy Content-Type header từ request
    """
    try:
        return request.headers.get("content-type")
    except Exception:
        return None

def get_request_info(request: Request) -> dict:
    """
    Lấy tất cả thông tin request quan trọng trong một dict
    Tiện cho việc logging
    """
    return {
        "ip_address": get_client_ip(request),
        "user_agent": get_user_agent(request),
        "method": get_request_method(request),
        "url": get_request_url(request),
        "path": get_request_path(request),
        "referer": get_referer(request),
        "content_type": get_content_type(request)
    }