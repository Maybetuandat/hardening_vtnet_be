from sqlalchemy.orm import Session

from dao.os_dao import OsDao
from models.os import Os
from schemas.os import OsCreate, OsListResponse, OsResponse, OsSearchParams, OsUpdate
class OsService:
    def __init__(self, db : Session):
        self.dao = OsDao(db)
    

    def create(self, osc_create : OsCreate) -> OsResponse:
        os_dict = osc_create.dict()
        new_os = Os(**os_dict)
        created_os = self.dao.create(new_os)
        return OsResponse.from_orm(created_os)
    def search(self, search_params: OsSearchParams) -> OsListResponse:
        offset = (search_params.page - 1) * search_params.size
        limit = search_params.size
        os_list, total = self.dao.search(
            keyword=search_params.keyword,
            offset=offset,
            limit=limit
        )
        total_pages = (total + search_params.size - 1) // search_params.size
        return OsListResponse(
            os=[OsResponse.from_orm(os) for os in os_list],
            total=total,
            page=search_params.page,
            page_size=search_params.size,
            total_pages=total_pages
        )
    def get_by_id(self, os_id: int) -> OsResponse:
        os = self.dao.get_by_id(os_id)
        if not os:
            return None
        return OsResponse.from_orm(os)
    def update(self, os_update: OsUpdate, os_id: int) -> OsResponse:

        exist_os = self.dao.get_by_id(os_id)
        if not exist_os:
            return None
        if os_update.version is not None:
            exist_os.version = os_update.version
        exist_os.up
        update_os = self.dao.update(exist_os)
        return OsResponse.from_orm(update_os)
    def delete(self, os_id: int) -> bool:
        return self.dao.delete(os_id)