from fastapi import FastAPI, Request, Form, HTTPException, Body
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
    # Fetch title from URL
    title = get_url_title(url)
    
    # Insert new link with simplified date format
    data = {
        "topic": topic,
        "url": url,
        "title": title,
        "source": source if source else "",
        "notes": notes if notes else "",
        "status": "new",  # Default status for new links
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    supabase.table('links').insert(data).execute()
    return RedirectResponse(url="/view", status_code=303)

@app.get("/view")
async def view_links(request: Request):
    response = supabase.table('links').select("*").order('id', desc=True).execute()
    links = response.data
    topics = get_topics()
    
    # Get unique non-empty sources
    sources = sorted(set(link['source'] for link in links if link['source']))
    
    return templates.TemplateResponse("view.html", {
        "request": request, 
        "links": links,
        "topics": topics,
        "sources": sources
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
    title: str = Form(...),
    status: str = Form(...),
    source: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    try:
        # Fetch current link data
        current_link = supabase.table('links').select("*").eq('id', id).execute()
        if not current_link.data:
            raise HTTPException(status_code=404, detail="Link not found")
        
        # Update title if URL has changed
        if url != current_link.data[0]['url']:
            title = get_url_title(url)
        
        data = {
            "topic": topic,
            "url": url,
            "source": source if source else "",
            "notes": notes if notes else "",
            "title": title,
            "status": status
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
    
    # Get unique non-empty sources
    sources = sorted(set(link['source'] for link in links if link['source']))
    
    return templates.TemplateResponse("manage_links.html", {
        "request": request,
        "topics": topics,
        "links": links,
        "sources": sources
    })

@app.get("/companies")
async def companies_page(request: Request):
    companies = supabase.table('companies').select("*").order('date', desc=True).execute().data
    return templates.TemplateResponse("companies.html", {
        "request": request,
        "companies": companies
    })

@app.post("/company/add")
async def add_company(
    name: str = Form(...),
    url: str = Form(...),
    notes: Optional[str] = Form(None)
):
    data = {
        "name": name,
        "url": url,
        "notes": notes if notes else "",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    supabase.table('companies').insert(data).execute()
    return RedirectResponse(url="/companies", status_code=303)

@app.post("/company/delete/{id}")
async def delete_company(id: int):
    supabase.table('companies').delete().eq('id', id).execute()
    return RedirectResponse(url="/companies", status_code=303)

@app.post("/company/edit/{id}")
async def edit_company(
    id: int,
    name: str = Form(...),
    url: str = Form(...),
    notes: Optional[str] = Form(None)
):
    data = {
        "name": name,
        "url": url,
        "notes": notes if notes else ""
    }
    
    supabase.table('companies').update(data).eq('id', id).execute()
    return RedirectResponse(url="/companies", status_code=303)

@app.post("/link/status/{id}")
async def update_link_status(id: int, status_data: dict = Body(...)):
    try:
        status = status_data.get('status')
        if not status:
            raise HTTPException(status_code=400, detail="Status is required")
            
        if status not in ['new', 'read', 'read-again']:
            raise HTTPException(status_code=400, detail="Invalid status value")
            
        data = {
            "status": status
        }
        
        result = supabase.table('links').update(data).eq('id', id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Link not found")
            
        return {"status": "success", "message": "Status updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos")
async def videos_page(request: Request):
    videos = supabase.table('videos').select("*").order('date', desc=True).execute().data
    topics = get_topics()
    return templates.TemplateResponse("videos.html", {
        "request": request,
        "videos": videos,
        "topics": topics
    })

@app.post("/video/add")
async def add_video(
    topic: str = Form(...),
    link: str = Form(...),
    notes: Optional[str] = Form(None)
):
    # Fetch title from URL
    title = get_url_title(link)
    
    data = {
        "topic": topic,
        "link": link,
        "title": title,
        "notes": notes if notes else "",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    supabase.table('videos').insert(data).execute()
    return RedirectResponse(url="/videos", status_code=303)

@app.post("/video/edit/{id}")
async def edit_video(
    id: int,
    topic: str = Form(...),
    link: str = Form(...),
    notes: Optional[str] = Form(None)
):
    try:
        # Fetch current video data
        current_video = supabase.table('videos').select("*").eq('id', id).execute()
        if not current_video.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Update title if URL has changed
        title = current_video.data[0]['title']
        if link != current_video.data[0]['link']:
            title = get_url_title(link)
        
        data = {
            "topic": topic,
            "link": link,
            "title": title,
            "notes": notes if notes else ""
        }
        
        result = supabase.table('videos').update(data).eq('id', id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update video")
            
        return RedirectResponse(url="/videos", status_code=303)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/delete/{id}")
async def delete_video(id: int):
    supabase.table('videos').delete().eq('id', id).execute()
    return RedirectResponse(url="/videos", status_code=303) 