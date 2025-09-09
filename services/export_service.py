import io
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
import pandas as pd

from dao.compliance_dao import ComplianceDAO
from schemas.compliance import ComplianceSearchParams


class ExportService:
    def __init__(self, db: Session):
        self.db = db
        self.compliance_dao = ComplianceDAO(db)

    def export_compliance_results_to_excel(
        self, 
        search_params: Optional[ComplianceSearchParams] = None
    ) -> bytes:
        """
        Xuất danh sách compliance results trong ngày hiện tại ra file Excel
        """
        try:
            # Lấy dữ liệu compliance results trong ngày hiện tại
            results = self.compliance_dao.get_today_compliance_results(
                list_workload_id=search_params.list_workload_id if search_params else None,
                keyword=search_params.keyword if search_params else None,
                status=search_params.status if search_params else None
            )

            # Chuẩn bị dữ liệu cho Excel
            excel_data = []
            
            for result in results:
                # Lấy thông tin server và workload đã được load sẵn qua joinedload
                server_ip = "N/A"
                workload_name = "N/A"
                
                if result.server:
                    server_ip = result.server.ip_address or "N/A"
                    if result.server.workload:
                        workload_name = result.server.workload.name or "N/A"

                excel_data.append({
                    "ID": result.id,
                    "Server IP": server_ip,
                    "Workload Name": workload_name,
                    "Status": result.status,
                    "Total Rules": result.total_rules,
                    "Passed Rules": result.passed_rules,
                    "Failed Rules": result.failed_rules,
                    "Score": float(result.score) if result.score else 0.0,
                    "Scan Date": result.scan_date.strftime("%Y-%m-%d %H:%M:%S") if result.scan_date else "",
                    "Created At": result.created_at.strftime("%Y-%m-%d %H:%M:%S") if result.created_at else "",
                    "Updated At": result.updated_at.strftime("%Y-%m-%d %H:%M:%S") if result.updated_at else ""
                })

            # Tạo DataFrame
            df = pd.DataFrame(excel_data)

            # Tạo file Excel trong memory
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Ghi dữ liệu vào sheet
                df.to_excel(writer, sheet_name='Compliance Results', index=False)
                
                # Lấy workbook và worksheet để format
                workbook = writer.book
                worksheet = writer.sheets['Compliance Results']
                
                # Tạo format cho header
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Format header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Auto-adjust column widths
                for i, col in enumerate(df.columns):
                    column_len = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    )
                    worksheet.set_column(i, i, min(column_len + 2, 30))
                
                # Freeze panes
                worksheet.freeze_panes(1, 0)

            output.seek(0)
            return output.read()

        except Exception as e:
            logging.error(f"Error exporting compliance results to Excel: {str(e)}")
            raise e

    def get_export_filename(self) -> str:
        """Tạo tên file Excel với ngày hiện tại"""
        today_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%H%M%S")
        return f"compliance_daily_report_{today_str}_{timestamp}.xlsx"