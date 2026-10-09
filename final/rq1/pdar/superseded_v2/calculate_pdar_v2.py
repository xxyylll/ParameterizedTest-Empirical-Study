import csv
import os
import re
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Configuration
PROJECT_LIST_FILE = '/Users/immortal/PT_Empirical_Auto/developer/pt_project.txt'
RESULT_DIR = '/Users/immortal/PT_Empirical_Auto/developer/result'
RESULT_DETAILED_DIR = '/Users/immortal/PT_Empirical_Auto/developer/result_detailed'
RESULT_V2_DIR = '/Users/immortal/PT_Empirical_Auto/developer/result_v2'
OUTPUT_CSV = '/Users/immortal/PT_Empirical_Auto/developer/result_v2/pdar_summary.csv'
HISTOGRAM_IMAGE = '/Users/immortal/PT_Empirical_Auto/developer/result_v2/pdar_histogram.png'
SCATTER_IMAGE = '/Users/immortal/PT_Empirical_Auto/developer/result_v2/pdar_scatter.png'

def parse_author_string(author_str):
    """
    Parses 'Name <email>' into (name, email).
    """
    match = re.match(r'^(.*?)\s*<(.*)>$', author_str)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        return name, email
    return author_str.strip(), ""

def count_unique_developers(author_list):
    """
    Counts unique developers based primarily on Email.
    If multiple entries have the same email, they count as one developer.
    If email is missing, Name is used as the key.
    Returns both count and the set of unique keys (for union operations).
    """
    unique_keys = set()
    
    for name, email in author_list:
        if email and email.strip():
            key = email.strip().lower()
        else:
            # Fallback to name if no email
            key = name.strip().lower()
            
        if key:
            unique_keys.add(key)
            
    return len(unique_keys), unique_keys


def get_unique_keys(author_list):
    """
    Returns the set of unique developer keys (primarily email-based).
    """
    unique_keys = set()
    
    for name, email in author_list:
        if email and email.strip():
            key = email.strip().lower()
        else:
            key = name.strip().lower()
            
        if key:
            unique_keys.add(key)
            
    return unique_keys

def process_project(project_name):
    # Paths for git log -G method (pickaxe only, no line history bias)
    pt_pickaxe_file = os.path.join(RESULT_DIR, f"{project_name}_developer_pickaxe.csv")
    test_authors_file = os.path.join(RESULT_DIR, f"{project_name}_test_file_authors.csv")
    
    # Paths for new diff+range method (detailed) - old version
    pt_detailed_file = os.path.join(RESULT_DETAILED_DIR, f"{project_name}_pt_developers.csv")
    
    # Paths for v2 lifecycle-based method (new comprehensive approach)
    pt_v2_file = os.path.join(RESULT_V2_DIR, f"{project_name}_pt_developers.csv")
    
    # Check existence of test authors file (required)
    if not os.path.exists(test_authors_file):
        print(f"[Warning] Missing authors file for {project_name}: {test_authors_file}")
        return None

    # 1. Read PT Developers from v2 lifecycle-based method (preferred)
    pt_authors_v2 = []
    if os.path.exists(pt_v2_file):
        with open(pt_v2_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('author_name', '').strip()
                email = row.get('author_email', '').strip()
                if name or email:
                    pt_authors_v2.append((name, email))
    else:
        print(f"  [Info] No v2 lifecycle result for {project_name}")
    
    # 2. Read PT Developers from git log -G (pickaxe) method (fallback)
    pt_authors_pickaxe = []
    if os.path.exists(pt_pickaxe_file):
        with open(pt_pickaxe_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # Skip header: Author,Commits
            if header:
                for row in reader:
                    if row:
                        full_str = row[0]  # "Name <email>"
                        name, email = parse_author_string(full_str)
                        pt_authors_pickaxe.append((name, email))
    else:
        print(f"  [Info] No pickaxe result for {project_name}")
    
    # 3. Read PT Developers from old diff+range method (deprecated, for comparison)
    pt_authors_detailed = []
    if os.path.exists(pt_detailed_file):
        with open(pt_detailed_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('author_name', '').strip()
                email = row.get('author_email', '').strip()
                if name or email:
                    pt_authors_detailed.append((name, email))
    
    # 4. Compute unique developer sets
    pt_keys_v2 = get_unique_keys(pt_authors_v2)
    pt_keys_pickaxe = get_unique_keys(pt_authors_pickaxe)
    pt_keys_detailed = get_unique_keys(pt_authors_detailed)
    
    # Use v2 if available, otherwise fall back to pickaxe+detailed union
    if pt_keys_v2:
        pt_keys_final = pt_keys_v2
    else:
        pt_keys_final = pt_keys_pickaxe | pt_keys_detailed
    
    # 5. Read All Test Developers (Denominator)
    test_authors = []
    with open(test_authors_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)  # Skip header
        # Header expected: Name,Email,Full_String
        name_idx = 0
        email_idx = 1
        
        if header and "Name" in header and "Email" in header:
            try:
                name_idx = header.index("Name")
                email_idx = header.index("Email")
            except ValueError:
                pass

        if header:
            for row in reader:
                if row and len(row) > max(name_idx, email_idx):
                    name = row[name_idx]
                    email = row[email_idx]
                    test_authors.append((name, email))

    # 6. Count unique developers
    num_pt_devs_v2 = len(pt_keys_v2)
    num_pt_devs_pickaxe = len(pt_keys_pickaxe)
    num_pt_devs_final = len(pt_keys_final)
    num_test_devs, _ = count_unique_developers(test_authors)
    
    # 7. Calculate PDAR
    if num_test_devs > 0:
        pdar = (num_pt_devs_final / num_test_devs) * 100
    else:
        pdar = 0.0
        
    return {
        'Project': project_name,
        'PT_Devs_V2': num_pt_devs_v2,
        'PT_Devs_Pickaxe': num_pt_devs_pickaxe,
        'PT_Devs_Final': num_pt_devs_final,
        'Test_Devs': num_test_devs,
        'PDAR': pdar
    }

def main():
    # Read project list
    with open(PROJECT_LIST_FILE, 'r') as f:
        projects = [line.strip() for line in f if line.strip()]
        
    results = []
    print(f"Processing {len(projects)} projects...")
    
    for proj in projects:
        data = process_project(proj)
        if data:
            results.append(data)
            print(f"  {proj}: V2={data['PT_Devs_V2']}, Pickaxe={data['PT_Devs_Pickaxe']}, "
                  f"Final={data['PT_Devs_Final']}, Total={data['Test_Devs']}, PDAR={data['PDAR']:.2f}%")
            
    # Save to CSV
    if results:
        fieldnames = ['Project', 'PT_Devs_V2', 'PT_Devs_Pickaxe', 'PT_Devs_Final', 'Test_Devs', 'PDAR']
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved CSV results to: {OUTPUT_CSV}")
        
        # Sort by PDAR for better visualization
        df = pd.DataFrame(results)
        df = df.sort_values('PDAR', ascending=True)
        
        # Generate Horizontal Bar Chart - shows each project clearly
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Create color gradient based on PDAR value
        colors = plt.cm.RdYlGn(df['PDAR'] / 100)  # Red-Yellow-Green colormap
        
        bars = ax.barh(df['Project'], df['PDAR'], color=colors, edgecolor='black', alpha=0.8)
        
        # Add value labels on each bar
        for bar, pdar, pt, total in zip(bars, df['PDAR'], df['PT_Devs_Final'], df['Test_Devs']):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{pdar:.1f}% ({pt}/{total})', 
                    va='center', ha='left', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('PDAR (%)', fontsize=12)
        ax.set_ylabel('Project', fontsize=12)
        ax.set_title('Parameterized Test Developer Adoption Rate (PDAR) by Project', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 105)  # Leave room for labels
        ax.axvline(x=df['PDAR'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {df["PDAR"].mean():.1f}%')
        ax.axvline(x=df['PDAR'].median(), color='blue', linestyle='--', linewidth=2, label=f'Median: {df["PDAR"].median():.1f}%')
        ax.legend(loc='lower right')
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(HISTOGRAM_IMAGE, dpi=300)
        print(f"Saved Bar Chart to: {HISTOGRAM_IMAGE}")
        plt.close()

        # Generate Dot Plot with project labels - another clear view
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Scatter plot with project positions
        scatter = ax.scatter(df['PDAR'], range(len(df)), 
                            s=200, c=df['PDAR'], cmap='RdYlGn', 
                            edgecolors='black', linewidths=1.5, vmin=60, vmax=100)
        
        # Add project names as y-axis labels
        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df['Project'], fontsize=10)
        
        # Add PDAR value next to each point
        for i, (pdar, proj) in enumerate(zip(df['PDAR'], df['Project'])):
            ax.annotate(f'{pdar:.1f}%', (pdar, i), textcoords="offset points", 
                       xytext=(10, 0), ha='left', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('PDAR (%)', fontsize=12)
        ax.set_title('PDAR Distribution Across Projects', fontsize=14, fontweight='bold')
        ax.axvline(x=df['PDAR'].mean(), color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'Mean: {df["PDAR"].mean():.1f}%')
        ax.axvline(x=df['PDAR'].median(), color='blue', linestyle='--', linewidth=2, alpha=0.7, label=f'Median: {df["PDAR"].median():.1f}%')
        ax.legend(loc='lower right')
        ax.grid(axis='x', alpha=0.3)
        ax.set_xlim(60, 100)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax, orientation='vertical', shrink=0.8)
        cbar.set_label('PDAR (%)', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(SCATTER_IMAGE, dpi=300)
        print(f"Saved Dot Plot to: {SCATTER_IMAGE}")
        plt.close()
        
    else:
        print("No results to save.")

if __name__ == "__main__":
    main()
