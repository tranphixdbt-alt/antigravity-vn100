"""
Charts generator module — Vẽ biểu đồ định giá Plotly và xuất ảnh tĩnh PNG bằng kaleido để nhúng vào báo cáo.
"""
import os
import plotly.graph_objects as go
import plotly.express as px
from typing import List

def generate_football_field_chart(
    blended_fv: float, 
    current_price: float, 
    intrinsic_fv: float, 
    relative_fv: float, 
    output_path: str
):
    """
    Tạo biểu đồ Football Field và lưu thành ảnh PNG.
    """
    fig = go.Figure()
    
    # Đường giá thị trường hiện tại
    fig.add_shape(
        type="line", x0=current_price, y0=-0.5, x1=current_price, y1=2.5,
        line=dict(color="#64748B", width=3, dash="dash")
    )
    
    # Range hợp lý ±15% cho 3 khoảng định giá
    fig.add_trace(go.Bar(
        y=["Định giá So sánh", "Định giá Nội tại", "Blended Giá trị"],
        x=[relative_fv * 0.3, intrinsic_fv * 0.3, blended_fv * 0.3],
        base=[relative_fv * 0.85, intrinsic_fv * 0.85, blended_fv * 0.85],
        orientation='h',
        marker=dict(color=["#3B82F6", "#10B981", "#8B5CF6"], opacity=0.8),
        width=0.4
    ))
    
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFC",
        font=dict(color="#1E293B", size=12),
        title="Khoảng Giá Trị Định Giá So Với Thị Giá",
        xaxis_title="Giá trị cổ phiếu (VND)",
        height=300,
        margin=dict(l=120, r=40, t=50, b=50)
    )
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path, engine="kaleido")

def generate_sensitivity_heatmap_chart(
    matrix: List[List[float]], 
    x_labels: List[str], 
    y_labels: List[str], 
    is_bank: bool,
    output_path: str
):
    """
    Tạo biểu đồ Heatmap độ nhạy 2 chiều và lưu thành ảnh PNG.
    """
    fig = px.imshow(
        matrix,
        labels=dict(x="WACC (%)" if not is_bank else "Chi phí vốn Re (%)", y="Tăng trưởng vĩnh viễn g (%)", color="Giá hợp lý"),
        x=x_labels,
        y=y_labels,
        color_continuous_scale="Viridis",
        text_auto=True
    )
    
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#1E293B", size=12),
        title="Bảng Độ Nhạy Định Giá 2 Chiều",
        height=350,
        margin=dict(l=80, r=40, t=50, b=50)
    )
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path, engine="kaleido")
