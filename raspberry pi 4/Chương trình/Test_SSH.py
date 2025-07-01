import paramiko
# Tạo một phiên bản client SSH
client = paramiko.SSHClient()
# Đặt chính sách tự động thêm khóa host mới vào tệp known_hosts
# (Sử dụng paramiko.RejectPolicy() hoặc paramiko.WarningPolicy() cho môi trường sản phẩm)
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Kết nối đến máy chủ từ xa
try:
    client.connect(hostname='192.168.0.106', # Thay đổi địa chỉ IP hoặc tên máy chủ
                   username='Dinhphuc',
                   password='01082008', # Hoặc sử dụng key_filename cho xác thực bằng khóa
                   port=22) # Cổng SSH mặc định
    print("✅ Đã kết nối thành công!")
except paramiko.AuthenticationException:
    print("❌ Xác thực thất bại. Vui lòng kiểm tra lại tên người dùng và mật khẩu/khóa.")
except paramiko.SSHException as e:
    print(f"❌ Lỗi kết nối SSH: {e}")
except Exception as e:
    print(f"❌ Đã xảy ra lỗi: {e}")
finally:
    # Đóng kết nối
    client.close()
