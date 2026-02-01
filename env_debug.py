
# Script to verify environment variables on Railway
import os

print("--- ENV DEBUG START ---")
print(f"RAILWAY_PUBLIC_DOMAIN: {os.environ.get('RAILWAY_PUBLIC_DOMAIN')}")
print(f"RENDER_EXTERNAL_HOSTNAME: {os.environ.get('RENDER_EXTERNAL_HOSTNAME')}")
print(f"ALLOWED_HOSTS: {os.environ.get('ALLOWED_HOSTS')}")
print("--- ENV DEBUG END ---")
