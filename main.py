from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from typing import Optional

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def get_url_title(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No title found"
        return title
    except:
        return "Could not fetch title"

def get_topics():
    response = supabase.table('topics').select('*').order('name').execute()
    return response.data

@app.get("/")
async def drop_page(request: Request):
    topics = get_topics()
    return templates.TemplateResponse("drop.html", {"request": request, "topics": topics})

@app.post("/submit")
async def submit_link(
    topic: str = Form(...),
    url: str = Form(...),
    source: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    # Get current count of links to generate ID
    response = supabase.table('links').select('id').execute()
    current_count = len(response.data)
    new_id = current_count + 1
    
    # Fetch title from URL
    title = get_url_title(url)
    
    # Insert new link with simplified date format
    data = {
        "id": new_id,
        "topic": topic,
        "url": url,
        "title": title,
        "source": source if source else "",
        "notes": notes if notes else "",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    supabase.table('links').insert(data).execute()
    return RedirectResponse(url="/view", status_code=303)

@app.get("/view")
async def view_links(request: Request):
    response = supabase.table('links').select("*").order('id', desc=True).execute()
    links = response.data
    return templates.TemplateResponse("view.html", {"request": request, "links": links})

@app.get("/manage")
async def manage_page(request: Request):
    topics = get_topics()
    links = supabase.table('links').select("*").order('id', desc=True).execute().data
    return templates.TemplateResponse("manage.html", {
        "request": request,
        "topics": topics,
        "links": links
    })

@app.post("/topic/add")
async def add_topic(name: str = Form(...)):
    # Check if topic already exists
    existing = supabase.table('topics').select("*").eq('name', name).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Topic already exists")
    
    supabase.table('topics').insert({"name": name}).execute()
    return RedirectResponse(url="/manage/topics", status_code=303)

@app.post("/topic/delete/{name}")
async def delete_topic(name: str):
    # Check if topic is in use
    links = supabase.table('links').select("*").eq('topic', name).execute()
    if links.data:
        raise HTTPException(status_code=400, detail="Cannot delete topic that is in use")
    
    supabase.table('topics').delete().eq('name', name).execute()
    return RedirectResponse(url="/manage/topics", status_code=303)

@app.post("/link/edit/{id}")
async def edit_link(
    id: int,
    topic: str = Form(...),
    url: str = Form(...),
    source: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    try:
        # Fetch current link data
        current_link = supabase.table('links').select("*").eq('id', id).execute()
        if not current_link.data:
            raise HTTPException(status_code=404, detail="Link not found")
        
        # Update title if URL has changed
        title = current_link.data[0]['title']
        if url != current_link.data[0]['url']:
            title = get_url_title(url)
        
        data = {
            "topic": topic,
            "url": url,
            "source": source if source else "",
            "notes": notes if notes else "",
            "title": title
        }
        
        # Update the link
        result = supabase.table('links').update(data).eq('id', id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update link")
            
        return RedirectResponse(url="/manage/links", status_code=303)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/link/delete/{id}")
async def delete_link(id: int):
    supabase.table('links').delete().eq('id', id).execute()
    return RedirectResponse(url="/manage/links", status_code=303)

@app.get("/manage/topics")
async def manage_topics(request: Request):
    topics = get_topics()
    return templates.TemplateResponse("manage_topics.html", {
        "request": request,
        "topics": topics
    })

@app.get("/manage/links")
async def manage_links(request: Request):
    topics = get_topics()
    links = supabase.table('links').select("*").order('id', desc=True).execute().data
    return templates.TemplateResponse("manage_links.html", {
        "request": request,
        "topics": topics,
        "links": links
    }) 