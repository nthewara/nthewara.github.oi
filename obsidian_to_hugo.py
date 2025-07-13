#!/usr/bin/env python3
"""
Obsidian to Hugo Converter

This script converts Obsidian markdown notes to Hugo-compatible format.
It processes markdown files from an Obsidian vault and:
1. Removes Obsidian-style backlinks ([[link]] format)
2. Processes and moves images to Hugo posts structure
3. Creates proper Hugo front matter
4. Organizes content into Hugo's folder structure
"""

import os
import re
import shutil
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import unicodedata


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    
    Args:
        text: The text to convert to a slug
        
    Returns:
        A URL-friendly slug string
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    # Remove leading/trailing hyphens
    return text.strip('-')


def remove_backlinks(content: str) -> str:
    """
    Remove Obsidian-style backlinks from markdown content.
    
    Handles:
    - [[Page Name]] -> Page Name
    - [[Page Name|Display Text]] -> Display Text
    
    Note: This preserves image embeds (![[image.png]]) which are handled separately.
    
    Args:
        content: The markdown content to process
        
    Returns:
        Content with backlinks removed
    """
    # Pattern to match [[link]] or [[link|display text]], but NOT ![[image]]
    pattern = r'(?<!\!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
    
    def replace_link(match):
        link_target = match.group(1)
        display_text = match.group(2)
        
        # If there's display text, use it; otherwise use the link target
        return display_text if display_text else link_target
    
    return re.sub(pattern, replace_link, content)


def extract_images(content: str, obsidian_folder: Path) -> Tuple[str, List[Tuple[str, Path]]]:
    """
    Extract image references from markdown content and find their file paths.
    
    Args:
        content: The markdown content to process
        obsidian_folder: Path to the Obsidian vault folder
        
    Returns:
        Tuple of (processed_content, list of (image_name, image_path) tuples)
    """
    images = []
    
    # Pattern to match Obsidian image embeds: ![[image.png]] or ![alt](image.png)
    obsidian_pattern = r'!\[\[([^\]]+)\]\]'
    markdown_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def find_image_file(image_name: str) -> Optional[Path]:
        """Find an image file in the Obsidian vault."""
        # Search for the image in the vault and common subdirectories
        search_paths = [
            obsidian_folder,
            obsidian_folder / "attachments",
            obsidian_folder / "images",
            obsidian_folder / "assets",
            obsidian_folder / "files"
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                # Look for the exact filename
                image_path = search_path / image_name
                if image_path.exists():
                    return image_path
                
                # Also search recursively in subdirectories
                for file_path in search_path.rglob(image_name):
                    if file_path.is_file():
                        return file_path
        
        return None
    
    def replace_obsidian_image(match):
        image_name = match.group(1)
        image_path = find_image_file(image_name)
        
        if image_path:
            images.append((image_name, image_path))
            # Convert to standard markdown format referencing local file
            return f'![{image_name}]({image_name})'
        else:
            print(f"Warning: Image '{image_name}' not found in Obsidian vault")
            return f'![{image_name}]({image_name})'
    
    def replace_markdown_image(match):
        alt_text = match.group(1)
        image_path_str = match.group(2)
        
        # If it's a relative path, try to find the file
        if not image_path_str.startswith(('http://', 'https://')):
            image_name = Path(image_path_str).name
            image_path = find_image_file(image_name)
            
            if image_path:
                images.append((image_name, image_path))
                return f'![{alt_text}]({image_name})'
        
        return match.group(0)  # Return original if external URL or not found
    
    # Process Obsidian-style image embeds
    content = re.sub(obsidian_pattern, replace_obsidian_image, content)
    
    # Process standard markdown images
    content = re.sub(markdown_pattern, replace_markdown_image, content)
    
    return content, images


def extract_title_from_content(content: str, filename: str) -> str:
    """
    Extract title from markdown content or use filename as fallback.
    
    Args:
        content: The markdown content
        filename: The original filename (without extension)
        
    Returns:
        Extracted or derived title
    """
    # Look for first H1 heading
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    # Look for any heading at the start
    heading_match = re.search(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()
    
    # Use filename as fallback
    return filename.replace('-', ' ').replace('_', ' ').title()


def create_hugo_frontmatter(title: str, date: datetime, tags: List[str] = None) -> str:
    """
    Create Hugo front matter in YAML format.
    
    Args:
        title: Post title
        date: Post date
        tags: Optional list of tags
        
    Returns:
        YAML front matter as string
    """
    frontmatter = {
        'title': title,
        'date': date.strftime('%Y-%m-%d'),
        'draft': False
    }
    
    if tags:
        frontmatter['tags'] = tags
    
    return '---\n' + yaml.dump(frontmatter, default_flow_style=False) + '---\n'


def process_obsidian_file(file_path: Path, obsidian_folder: Path, hugo_posts_dir: Path) -> bool:
    """
    Process a single Obsidian markdown file and convert it to Hugo format.
    
    Args:
        file_path: Path to the Obsidian markdown file
        obsidian_folder: Path to the Obsidian vault folder
        hugo_posts_dir: Path to Hugo's posts directory
        
    Returns:
        True if processing was successful, False otherwise
    """
    try:
        # Read the original file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title and create slug
        filename_stem = file_path.stem
        title = extract_title_from_content(content, filename_stem)
        post_slug = slugify(title)
        
        # Create post directory
        post_dir = hugo_posts_dir / post_slug
        post_dir.mkdir(parents=True, exist_ok=True)
        
        # Process content: remove backlinks and extract images
        content = remove_backlinks(content)
        content, images = extract_images(content, obsidian_folder)
        
        # Copy images to post directory
        copied_images = set()
        for image_name, image_path in images:
            if image_name not in copied_images:
                dest_path = post_dir / image_name
                try:
                    shutil.copy2(image_path, dest_path)
                    copied_images.add(image_name)
                    print(f"Copied image: {image_name}")
                except Exception as e:
                    print(f"Warning: Failed to copy image {image_name}: {e}")
            # If already copied, skip but don't warn (multiple references to same image are OK)
        
        # Create Hugo front matter
        creation_date = datetime.fromtimestamp(file_path.stat().st_mtime)
        frontmatter = create_hugo_frontmatter(title, creation_date)
        
        # Write the Hugo post
        hugo_content = frontmatter + '\n' + content
        index_path = post_dir / 'index.md'
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(hugo_content)
        
        print(f"Successfully processed: {title} -> {post_slug}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def convert_obsidian_to_hugo(obsidian_folder: str, hugo_root: str = None) -> None:
    """
    Convert all markdown files from Obsidian vault to Hugo format.
    
    Args:
        obsidian_folder: Path to the Obsidian vault folder
        hugo_root: Path to Hugo site root (defaults to current directory)
    """
    obsidian_path = Path(obsidian_folder)
    if not obsidian_path.exists():
        print(f"Error: Obsidian folder '{obsidian_folder}' does not exist")
        return
    
    # Set up Hugo paths
    hugo_root_path = Path(hugo_root) if hugo_root else Path.cwd()
    hugo_posts_dir = hugo_root_path / 'content' / 'posts'
    
    # Create posts directory if it doesn't exist
    hugo_posts_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all markdown files in Obsidian vault
    markdown_files = list(obsidian_path.rglob('*.md'))
    
    if not markdown_files:
        print(f"No markdown files found in '{obsidian_folder}'")
        return
    
    print(f"Found {len(markdown_files)} markdown files to process")
    
    successful = 0
    failed = 0
    
    for md_file in markdown_files:
        if process_obsidian_file(md_file, obsidian_path, hugo_posts_dir):
            successful += 1
        else:
            failed += 1
    
    print(f"\nConversion complete:")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {failed}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert Obsidian markdown notes to Hugo format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python obsidian_to_hugo.py /path/to/obsidian/vault
  python obsidian_to_hugo.py /path/to/obsidian/vault --hugo-root /path/to/hugo/site
        """
    )
    
    parser.add_argument(
        'obsidian_folder',
        help='Path to the Obsidian vault folder containing markdown files'
    )
    
    parser.add_argument(
        '--hugo-root',
        default=None,
        help='Path to Hugo site root directory (defaults to current directory)'
    )
    
    args = parser.parse_args()
    
    print("Obsidian to Hugo Converter")
    print("=" * 25)
    print(f"Obsidian folder: {args.obsidian_folder}")
    print(f"Hugo root: {args.hugo_root or 'current directory'}")
    print()
    
    convert_obsidian_to_hugo(args.obsidian_folder, args.hugo_root)


if __name__ == '__main__':
    main()