# Droplink

A simple application to store and view links with notes using FastAPI and Supabase.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your Supabase credentials:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. Create a table in your Supabase database with the following structure:
```sql
create table links (
    id integer primary key,
    topic text not null,
    url text not null,
    description text not null,
    notes text,
    date timestamp with time zone not null
);
```

5. Run the application:
```bash
uvicorn main:app --reload
```

## Usage

- Visit `http://localhost:8000` to access the drop page
- Fill in the form with your link details
- Click "Submit" to save the link
- Visit `http://localhost:8000/view` to see all saved links

## Features

- Simple and clean interface
- Responsive design
- Automatic ID and date generation
- View all links in a card layout
- Direct link to the original URL 