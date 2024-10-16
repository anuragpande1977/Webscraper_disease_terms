import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from Bio import Entrez

# BioPython Entrez setup
Entrez.email = "your-email@example.com"  # Replace with your email for PubMed access

# Streamlit UI
st.title("Disease Term Web Scraper Using BioPython (PubMed)")

# Input for base URL
base_url = st.text_input('Enter the website URL to scrape:', 'https://www.example.com')

# Input for scraping depth
max_depth = st.slider('Choose the scraping depth:', 1, 5, 2)

# Input for disease terms
user_terms = st.text_area("Enter disease terms (comma-separated):", "cancer, diabetes, hypertension")

# Parse the user input
disease_terms = [term.strip() for term in user_terms.split(',')]

# Function to fetch MeSH terms from PubMed using BioPython
def fetch_mesh_terms(query):
    try:
        # Search for MeSH terms related to the query
        handle = Entrez.esearch(db="mesh", term=query, retmax=1)
        record = Entrez.read(handle)
        handle.close()

        # If no results found, return the original query
        if not record['IdList']:
            st.warning(f"No MeSH terms found for '{query}'")
            return [query]

        mesh_id = record["IdList"][0]
        
        # Fetch the MeSH record details
        fetch_handle = Entrez.efetch(db="mesh", id=mesh_id, retmode="xml")
        data = Entrez.read(fetch_handle)
        fetch_handle.close()

        # Extract MeSH terms and synonyms
        term_list = [data[0]["DescriptorName"][0]]  # Add the primary MeSH term
        for concept in data[0]["ConceptList"]:
            for term in concept["TermList"]:
                term_list.append(term["String"])

        return term_list

    except Exception as e:
        st.error(f"Error fetching MeSH terms: {e}")
        return [query]

# Function to expand disease terms with MeSH synonyms
def expand_disease_terms(disease_terms):
    expanded_terms = set()
    for term in disease_terms:
        mesh_terms = fetch_mesh_terms(term)
        expanded_terms.update(mesh_terms)
    return expanded_terms

# Function to scrape a single page for disease terms
def scrape_page(url, disease_terms):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get all the text content on the page
        page_text = soup.get_text().lower()
        
        # Look for disease terms in the page text
        found_terms = {term.lower() for term in disease_terms if term.lower() in page_text}
        
        return found_terms
    except Exception as e:
        st.warning(f"Error scraping {url}: {e}")
        return set()

# Function to recursively scrape a website and its subpages
def scrape_website(base_url, disease_terms, max_depth=2, visited=None):
    if visited is None:
        visited = set()
    
    # If we've already visited this URL, return
    if base_url in visited or max_depth == 0:
        return {}
    
    st.write(f"Scraping {base_url}")
    
    # Mark this URL as visited
    visited.add(base_url)
    
    # Scrape the base page for disease terms
    found_terms = scrape_page(base_url, disease_terms)
    
    # Now find all the subpages to scrape
    try:
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all the links on the page
        links = soup.find_all('a', href=True)
        
        # Recursively scrape each link that belongs to the same website
        for link in links:
            full_url = urljoin(base_url, link['href'])
            if base_url in full_url and full_url not in visited:
                subpage_terms = scrape_website(full_url, disease_terms, max_depth - 1, visited)
                found_terms.update(subpage_terms)
    
    except Exception as e:
        st.warning(f"Error processing subpages for {base_url}: {e}")
    
    return found_terms

# Run the scraper when the button is pressed
if st.button('Start Scraping'):
    if base_url and disease_terms:
        # Expand disease terms using BioPython (MeSH)
        expanded_disease_terms = expand_disease_terms(disease_terms)
        st.write(f"Expanded Disease Terms (with MeSH): {expanded_disease_terms}")
        
        # Scrape the website
        found_disease_terms = scrape_website(base_url, expanded_disease_terms, max_depth=max_depth)
        
        # Display results
        if found_disease_terms:
            st.success(f"Found the following disease terms: {found_disease_terms}")
        else:
            st.warning("No disease terms found.")
