sed -i '' 's/DATABASE_URL_WRITE=postgresql:\/\/readonly_user:readonly_pass/DATABASE_URL_WRITE=postgresql:\/\/write_user:write_pass/g' .env
