import streamlit as st
from groq import Groq
import json
from datetime import datetime
from typing import Dict, Any

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = "api_input"
if 'approved' not in st.session_state:
    st.session_state.approved = {}
if 'feedback' not in st.session_state:
    st.session_state.feedback = {}
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = {}
# Add to the top with other session state initializations
if 'show_completion_prompt' not in st.session_state:
    st.session_state.show_completion_prompt = False


# Add Font Awesome CSS
st.markdown(
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">',
    unsafe_allow_html=True
)

# SDLC workflow steps with colored icons
WORKFLOW_STEPS = [
    {"id": "api_input", "label": "🤖 AI Powered Automation", "icon": "fa-key", "color": "#2196F3"},
    {"id": "user_stories", "label": "User Stories", "icon": "fa-clipboard-list", "color": "#4CAF50"},
    {"id": "design_docs", "label": "Design Docs", "icon": "fa-drafting-compass", "color": "#FF9800"},
    {"id": "code_generation", "label": "Code Generation", "icon": "fa-code", "color": "#9C27B0"},
    {"id": "code_review", "label": "Code Review", "icon": "fa-search-plus", "color": "#00BCD4"},
    {"id": "security_review", "label": "Security Review", "icon": "fa-shield-alt", "color": "#F44336"},
    {"id": "test_cases", "label": "Test Cases", "icon": "fa-vial", "color": "#8BC34A"},
    {"id": "qa_testing", "label": "QA Testing", "icon": "fa-check-double", "color": "#3F51B5"},
    {"id": "deployment", "label": "Deployment", "icon": "fa-rocket", "color": "#E91E63"},
    {"id": "monitoring", "label": "Monitoring", "icon": "fa-chart-line", "color": "#009688"}
]

# AI prompt templates
PROMPT_TEMPLATES = {
    "user_stories": "Generate comprehensive user stories for: {prompt}. Include acceptance criteria.",
    "design_docs": """Create functional and technical design documents for: {prompt}
    Functional:
    - User flows
    - Feature specs
    
    Technical:
    - Architecture
    - Tech stack
    - Data models""",
    "code_generation": "Generate production-ready code for: {prompt}. Include error handling and docs.",
    "test_cases": "Create test cases for: {prompt}. Include positive/negative scenarios.",
    "deployment": "Create deployment plan for: {prompt}. Include rollback strategy."
}

def generate_with_groq(prompt: str, step: str) -> str:
    """Generate content using Groq API"""
    try:
        client = Groq(api_key=st.session_state.api_key)
        system_prompt = f"Expert SDLC assistant. Provide detailed output for {step}."
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return ""

def get_download_filename(prefix: str) -> str:
    """Generate standardized filename"""
    project_name = (st.session_state.project_prompt[:20] 
                    if 'project_prompt' in st.session_state 
                    else "project").replace(" ", "_")
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{prefix}_{project_name}_{date_str}"

# Modify the download_entire_workflow function
def download_entire_workflow():
    """Prepare complete workflow data for download"""
    workflow_data = {
        "project": st.session_state.get('project_prompt', ''),
        "timestamp": datetime.now().isoformat(),
        "steps": {}
    }
    
    for step in WORKFLOW_STEPS:
        step_id = step["id"]
        if step_id in st.session_state.generated_content:
            workflow_data["steps"][step_id] = {
                "content": st.session_state.generated_content[step_id],
                "feedback": st.session_state.feedback.get(step_id, ""),
                "approved": st.session_state.approved.get(step_id, False)
            }
    
    # Check if all steps are approved
    if check_workflow_completion():
        st.session_state.show_completion_prompt = True
    
    return json.dumps(workflow_data, indent=2)

def render_step(step_id: str):
    """Render current workflow step"""
    step_info = next((s for s in WORKFLOW_STEPS if s["id"] == step_id), None)
    if not step_info:
        st.error("Invalid step")
        return
    
    st.header(step_info["label"])
    
    if step_id == "api_input":
        render_api_input()
    else:
        render_sdlc_step(step_id)

def render_api_input():
    """Render API key and project input"""
    st.session_state.api_key = st.text_input("Groq API Key:", type="password")
    st.session_state.project_prompt = st.text_area(
        "Project Description:",
        placeholder="Describe your project (e.g., 'Smart pen with IoT capabilities')"
    )
    
    if st.button("Start SDLC Workflow"):
        if not st.session_state.api_key:
            st.warning("Please enter API key")
        elif not st.session_state.project_prompt:
            st.warning("Please enter project description")
        else:
            st.session_state.current_step = "user_stories"
            st.rerun()

def render_sdlc_step(step_id: str):
    """Render SDLC step with approval flow"""
    if step_id not in st.session_state.generated_content or st.session_state.feedback.get(step_id):
        prompt = PROMPT_TEMPLATES.get(step_id, "").format(prompt=st.session_state.project_prompt)
        if st.session_state.feedback.get(step_id):
            prompt += f"\n\nFeedback: {st.session_state.feedback[step_id]}"
        
        with st.spinner(f"Generating {step_id.replace('_', ' ')}..."):
            st.session_state.generated_content[step_id] = generate_with_groq(prompt, step_id)
    
    st.markdown(st.session_state.generated_content[step_id])
    
    # Controls
    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button(f"✅ Approve", key=f"approve_{step_id}"):
            st.session_state.approved[step_id] = True
            move_to_next_step()
    with col2:
        with st.expander("Request Changes"):
            feedback = st.text_area("Feedback:", key=f"feedback_{step_id}")
            if st.button("Submit", key=f"submit_{step_id}"):
                if feedback:
                    st.session_state.feedback[step_id] = feedback
                    st.session_state.approved[step_id] = False
                    st.rerun()
                else:
                    st.warning("Please enter feedback")
    with col3:
        if st.session_state.generated_content.get(step_id):
            st.download_button(
                label=f"📥 Download {step_id.replace('_', ' ')}",
                data=st.session_state.generated_content[step_id],
                file_name=f"{get_download_filename(step_id)}.txt",
                mime="text/plain",
                key=f"download_{step_id}"
            )

def move_to_next_step():
    """Progress to next workflow step"""
    current_index = next(i for i, s in enumerate(WORKFLOW_STEPS) if s["id"] == st.session_state.current_step)
    if current_index < len(WORKFLOW_STEPS) - 1:
        st.session_state.current_step = WORKFLOW_STEPS[current_index + 1]["id"]
        st.rerun()

# Add this function
def check_workflow_completion():
    """Check if all steps are completed"""
    approved_steps = [s for s in WORKFLOW_STEPS if s['id'] != 'api_input' 
                     and st.session_state.approved.get(s['id'], False)]
    return len(approved_steps) == len(WORKFLOW_STEPS) - 1

# Sidebar - Workflow Navigation
with st.sidebar:
    st.markdown("""
    <style>
    .sidebar-step {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .sidebar-step:hover {
        background-color: #f0f2f6;
        transform: translateX(5px);
    }
    .current-step {
        background-color: #e1f5fe;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .step-icon {
        margin-right: 0.75rem;
        font-size: 1.2rem;
        min-width: 1.8rem;
        text-align: center;
    }
    .step-label {
        flex-grow: 1;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("SDLC Workflow")
    
    for step in WORKFLOW_STEPS:
        is_current = step["id"] == st.session_state.current_step
        step_class = "current-step" if is_current else ""
        
        st.markdown(
            f"""
            <div class="sidebar-step {step_class}" onclick="window.location.href='?step={step['id']}'">
                <i class="fas {step['icon']} step-icon" style="color: {step['color']};"></i>
                <span class="step-label">{step['label']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Progress and download
    st.divider()
    approved_count = sum(st.session_state.approved.values())
    total_steps = len(WORKFLOW_STEPS) - 1
    st.progress(approved_count / total_steps if total_steps > 0 else 0, 
               text=f"Progress: {approved_count}/{total_steps} approved")
    
    if st.session_state.current_step != "api_input":
        st.download_button(
            label="📦 Download Full Workflow",
            data=download_entire_workflow(),
            file_name=f"{get_download_filename('full_workflow')}.json",
            mime="application/json",
            key="download_full"
        )
# Add this at the end of the main content rendering
def render_completion_prompt():
    """Show completion dialog"""
    st.success("🎉 SDLC workflow completed and downloaded successfully!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Start New SDLC"):
            # Reset session state but keep API key
            api_key = st.session_state.get('api_key', '')
            st.session_state.clear()
            st.session_state.api_key = api_key
            st.session_state.show_completion_prompt = False
            st.rerun()
    
    with col2:
        if st.button("🚪 Quit"):
            st.markdown("### Thank you for using SDLC Assistant!")
            st.markdown("> You can safely close this browser tab.")
            st.stop()

# Main content area
if st.session_state.show_completion_prompt:
    render_completion_prompt()
else:
    render_step(st.session_state.current_step)