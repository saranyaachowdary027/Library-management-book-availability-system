# Deploy the editable library app

This Streamlit app can add books and save borrow/return transactions. For hosted use, it connects to PostgreSQL; the included SQLite database is imported once if the hosted tables are empty. Hosted access is protected by a staff password.

## Set up the database

1. Create a PostgreSQL project in Supabase.
2. In the Supabase dashboard, open **Connect** and copy the **Session pooler** connection string. Use the value shown there; do not compose the hostname yourself.
3. Keep the database password private. Never commit it to GitHub or paste it into chat.

## Deploy the app

1. Sign in to Streamlit Community Cloud using the GitHub account that owns this repository.
2. Create an app from repository `saranyaachowdary027/Library-management-book-availability-system`, branch `live-library-app`, entrypoint `dashboard/app.py`.
3. In **Advanced settings → Secrets**, enter:

```toml
DATABASE_URL = "postgresql://postgres.<project-ref>:<password>@<session-pooler-host>:5432/postgres"
APP_PASSWORD = "<choose-a-private-staff-password>"
```

Replace the example with the complete session-pooler connection string supplied by Supabase. URL-encode any reserved characters in the password. The app converts the PostgreSQL URL for its driver. Do not put real credentials in this file or in GitHub.

The app will create its tables and load the repository's included SQLite snapshot once when the hosted tables are empty. Use **Add a Book** to add catalogue records and **Borrow & Return** to record circulation. Anyone who can reach the app still needs the staff password to view or change records.

## Important storage note

The app writes hosted changes to PostgreSQL. The local SQLite file is used only when `DATABASE_URL` is not configured. Community Cloud does not guarantee that local files will persist across restarts, so do not deploy editable shared data without the hosted database setting.
