import io
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
import pandas as pd

from dao.compliance_result_dao import ComplianceDAO
from dao.rule_dao import RuleDAO
from dao.rule_result_dao import RuleResultDAO
from schemas.compliance_result import ComplianceSearchParams


class ExportService:
    def __init__(self, db: Session):
        self.db = db
        self.compliance_dao = ComplianceDAO(db)
        self.rule_result_dao = RuleResultDAO(db)
        self.rule_dao = RuleDAO(db)

    def export_compliance_results_to_excel(
        self, 
        search_params: Optional[ComplianceSearchParams] = None
    ) -> bytes:
        """
        Xuất danh sách compliance results trong ngày hiện tại ra file Excel với 2 sheet:
        - Sheet 1: Compliance Results tổng quan
        - Sheet 2: Failed Rules Report chi tiết
        """
        try:
            # Lấy dữ liệu compliance results trong ngày hiện tại
            results = self.compliance_dao.get_today_compliance_results(
                list_workload_id=search_params.list_workload_id if search_params else None,
                keyword=search_params.keyword if search_params else None,
                status=search_params.status if search_params else None
            )

            # Tạo file Excel trong memory
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Tạo Sheet 1: Compliance Results tổng quan
                self._create_compliance_overview_sheet(writer, results)
                
                # Tạo Sheet 2: Failed Rules Report chi tiết
                self._create_failed_rules_report_sheet(writer, results)

            output.seek(0)
            return output.read()

        except Exception as e:
            logging.error(f"Error exporting compliance results to Excel: {str(e)}")
            raise e

    def _create_compliance_overview_sheet(self, writer, results):
        """Tạo sheet tổng quan compliance results"""
        # Chuẩn bị dữ liệu cho Excel
        excel_data = []
        
        for result in results:
            server_ip = "N/A"
            workload_name = "N/A"
            server_hostname = "N/A"
            
            if result.server:
                server_ip = result.server.ip_address or "N/A"
                server_hostname = result.server.hostname or "N/A"
                if result.server.workload:
                    workload_name = result.server.workload.name or "N/A"

            excel_data.append({
                "ID": result.id,
                "Server IP": server_ip,
                "Server Hostname": server_hostname,
                "Workload Name": workload_name,
                "Compliane Name": result.name,
                "Status": result.status,
                "Total Rules": result.total_rules,
                "Passed Rules": result.passed_rules,
                "Failed Rules": result.failed_rules,
                "Score": float(result.score) if result.score else 0.0,
                "Scan Date": result.scan_date.strftime("%Y-%m-%d %H:%M:%S") if result.scan_date else "",   
                "Updated At": result.updated_at.strftime("%Y-%m-%d %H:%M:%S") if result.updated_at else "",
                "Detail Error": result.detail_error or ""
            })

        
        df = pd.DataFrame(excel_data)

        
        df.to_excel(writer, sheet_name='Compliance Overview', index=False)
        
        
        self._format_compliance_overview_sheet(writer, df)

    def _format_compliance_overview_sheet(self, writer, df):
        
        workbook = writer.book
        worksheet = writer.sheets['Compliance Overview']
        
            # Tạo format cho header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        
        status_formats = {
            'completed': workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}),
            'failed': workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}),
            'pending': workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'}),
            'running': workbook.add_format({'bg_color': '#B4C7E7', 'font_color': '#1F4E79'})
        }
        
        # Format header row
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Format status column với màu sắc
        status_col_index = df.columns.get_loc('Status')
        for row_num in range(1, len(df) + 1):
            status_value = df.iloc[row_num - 1]['Status']
            if status_value in status_formats:
                worksheet.write(row_num, status_col_index, status_value, status_formats[status_value])
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            column_len = max(
                df[col].astype(str).map(len).max(),
                len(str(col))
            )
            worksheet.set_column(i, i, min(column_len + 2, 40))
        
        # Freeze panes
        worksheet.freeze_panes(1, 0)

    def _create_failed_rules_report_sheet(self, writer, compliance_results):
        """Tạo sheet báo cáo rule lỗi chi tiết"""
        failed_rules_data = []
        
        # Lặp qua từng compliance result để lấy failed rules
        for compliance in compliance_results:
            # Lấy tất cả failed rules của compliance này
            failed_rules = self.rule_result_dao.get_by_compliance_id(
                compliance_id=compliance.id,
                skip=0,
                limit=1000,  # Lấy nhiều để đảm bảo có đầy đủ data
                status="failed"  # Chỉ lấy rules failed
            )
            
            # Thông tin server và workload
            server_ip = "N/A"
            server_hostname = "N/A"
            workload_name = "N/A"
            
            if compliance.server:
                server_ip = compliance.server.ip_address or "N/A"
                server_hostname = compliance.server.hostname or "N/A"
                if compliance.server.workload:
                    workload_name = compliance.server.workload.name or "N/A"
            
            # Thêm từng failed rule vào data
            for rule_result in failed_rules:
                rule = self.rule_dao.get_by_id(rule_result.rule_id)

                failed_rules_data.append({
                    "Compliance ID": compliance.id,
                    
                    "Server IP": server_ip,
                    "Server Hostname": server_hostname,
                    "Workload Name": workload_name,
                    "Rule Name": rule.name if rule else "N/A",
                    "Output": rule_result.output or "",
                    "Parameters Rule": rule.parameters if rule else {},
                    "Error Message": rule_result.message or "",
                    "Error Details": rule_result.details_error or "",
                    "Scan Date": compliance.scan_date.strftime("%Y-%m-%d %H:%M:%S") if compliance.scan_date else "",
                    "Rule Updated At": rule_result.updated_at.strftime("%Y-%m-%d %H:%M:%S") if rule_result.updated_at else ""
                })
        
        # Tạo DataFrame cho failed rules
        failed_rules_df = pd.DataFrame(failed_rules_data)
        
        # Nếu không có failed rules nào, tạo một row thông báo
        if failed_rules_df.empty:
            failed_rules_df = pd.DataFrame([{
                 "Compliance ID": "",
                    
                    "Server IP": "",
                    "Server Hostname": "",
                    "Workload Name": "",
                    "Rule Name": "",
                    "Output": "",
                    "Parameters Rule":  {},
                    "Error Message":  "",
                    "Error Details":  "",
                    "Scan Date": "",
                    "Rule Updated At":  ""
            }])
        
        # Ghi dữ liệu vào sheet
        failed_rules_df.to_excel(writer, sheet_name='Failed Rules Report', index=False)
        
        # Format sheet
        self._format_failed_rules_sheet(writer, failed_rules_df)

    def _format_failed_rules_sheet(self, writer, df):
        """Format sheet báo cáo failed rules"""
        workbook = writer.book
        worksheet = writer.sheets['Failed Rules Report']
        
        # Tạo format cho header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#FFC7CE',  # Màu đỏ nhạt cho failed rules
            'font_color': '#9C0006',
            'border': 1
        })
        
        # Format cho compliance status
        compliance_status_formats = {
            'completed': workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}),
            'failed': workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}),
            'pending': workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'}),
            'running': workbook.add_format({'bg_color': '#B4C7E7', 'font_color': '#1F4E79'})
        }
        
        # Format cho rule status
        rule_status_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006',
            'bold': True
        })
        
        # Format header row
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Format các cột đặc biệt
        if 'Compliance Status' in df.columns:
            compliance_status_col_index = df.columns.get_loc('Compliance Status')
            for row_num in range(1, len(df) + 1):
                if row_num - 1 < len(df):
                    status_value = df.iloc[row_num - 1]['Compliance Status']
                    if status_value in compliance_status_formats:
                        worksheet.write(row_num, compliance_status_col_index, status_value, 
                                      compliance_status_formats[status_value])
        
        if 'Rule Status' in df.columns:
            rule_status_col_index = df.columns.get_loc('Rule Status')
            for row_num in range(1, len(df) + 1):
                if row_num - 1 < len(df):
                    rule_status_value = df.iloc[row_num - 1]['Rule Status']
                    if rule_status_value == 'failed':
                        worksheet.write(row_num, rule_status_col_index, rule_status_value, rule_status_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            if not df.empty and col in df.columns:
                column_len = max(
                    df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                    len(str(col))
                )
                worksheet.set_column(i, i, min(column_len + 2, 50))  # Tăng max width cho error details
        
        # Freeze panes
        worksheet.freeze_panes(1, 0)
        
        # Thêm filter cho tất cả các cột
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

    def get_export_filename(self) -> str:
        """Tạo tên file Excel với ngày hiện tại"""
        today_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%H%M%S")
        return f"compliance_daily_report_{today_str}_{timestamp}.xlsx"