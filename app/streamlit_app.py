import os
from hashlib import blake2b
from tempfile import NamedTemporaryFile
import replicate

import dotenv
from grobid_client.grobid_client import GrobidClient
import replicate.account
from streamlit_pdf_viewer import pdf_viewer
from openai import OpenAI

from grobid.grobid_processor import GrobidProcessor
from functools import partial

import streamlit as st

dotenv.load_dotenv(override=True)


st.set_page_config(
    page_title="Paperx with Llama2 ChatBot",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/lfoppiano/pdf-struct",
        "Report a bug": "https://github.com/lfoppiano/pdf-struct/issues",
        "About": "View the structures extracted by Grobid, with flavour of Llama2",
    },
)

### ---------- Set Frontend session's states ---------- ###
if "doc_id" not in st.session_state:
    st.session_state["doc_id"] = None

if "hash" not in st.session_state:
    st.session_state["hash"] = None

if "git_rev" not in st.session_state:
    st.session_state["git_rev"] = "unknown"
    if os.path.exists("revision.txt"):
        with open("revision.txt", "r") as fr:
            from_file = fr.read()
            st.session_state["git_rev"] = from_file if len(from_file) > 0 else "unknown"

if "uploaded" not in st.session_state:
    st.session_state["uploaded"] = False

if "binary" not in st.session_state:
    st.session_state["binary"] = None

if "annotations" not in st.session_state:
    st.session_state["annotations"] = []

if "pages" not in st.session_state:
    st.session_state["pages"] = None

if "page_selection" not in st.session_state:
    st.session_state["page_selection"] = []

if "segments" not in st.session_state.keys():
    st.session_state["segments"] = []

if "messages" not in st.session_state.keys():
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "How may I assist you today? I will be providing you with highly technical and detailed information!",
        }
    ]

if "llama" not in st.session_state:
    st.session_state["llama"] = None


### ---------- Methods ---------- ###
def new_file():
    st.session_state["doc_id"] = None
    st.session_state["uploaded"] = True
    st.session_state["annotations"] = []
    st.session_state["binary"] = None


@st.cache_resource
def init_grobid():
    try:
        grobid_client = GrobidClient(config_path="./config.json")
        grobid_processor = GrobidProcessor(grobid_client)

        return grobid_processor
    except:
        return None


@st.cache_resource
def get_llama():
    try:
        client = OpenAI(
            base_url="http://localhost:8080/v1",
            api_key="tom",
        )
        return client
    except:
        return None


def get_file_hash(fname):
    hash_md5 = blake2b()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def clear_chat_history():
    st.session_state.messages = [
        {"role": "assistant", "content": "How may I assist you today?"}
    ]


def generate_llama2_response(prompt_input):
    string_dialogue = "You are a helpful assistant. You do not respond as 'User' or pretend to be 'User'. You only respond once as 'Assistant'."
    for dict_message in st.session_state.messages:
        if dict_message["role"] == "user":
            string_dialogue += "User: " + dict_message["content"] + "\n\n"
        else:
            string_dialogue += "Assistant: " + dict_message["content"] + "\n\n"
    output = replicate.run(
        "a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5",
        input={
            "prompt": f"{string_dialogue} {prompt_input} Assistant: ",
            "temperature": temperature,
            "top_p": top_p,
            "max_length": max_length,
            "repetition_penalty": 1,
        },
    )
    return output


def write_prompt(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)


def llama_answer(prompt):
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_llama2_response(prompt)
                placeholder = st.empty()
                full_response = ""
                for item in response:
                    full_response += item
                    placeholder.markdown(full_response)
                placeholder.markdown(full_response)
        message = {"role": "assistant", "content": full_response}
        st.session_state.messages.append(message)


def llama_write_answer(prompt):
    write_prompt(prompt)
    llama_answer(prompt)


### ---------- Sidebar ---------- ###
with st.sidebar:
    ### ---------- Setting up Llama parameters ---------- ###
    st.markdown("# 🦙💬 Llama 2 Chatbot")
    if os.environ.get("REPLICATE_API_TOKEN"):
        st.success("API key already provided!", icon="✅")
        replicate_api = os.environ.get("REPLICATE_API_TOKEN")
    else:
        replicate_api = st.text_input("Enter Replicate API token:", type="password")
        if not (replicate_api.startswith("r8_") and len(replicate_api) == 40):
            st.warning("Please enter your credentials!", icon="⚠️")
        else:
            st.success("Proceed to entering your prompt message!", icon="👉")
    os.environ["REPLICATE_API_TOKEN"] = replicate_api
    st.markdown("## Models and parameters")
    selected_model = st.sidebar.selectbox(
        "Choose a Llama2 model", ["Llama2-7B", "Llama2-13B"], key="selected_model"
    )
    if selected_model == "Llama2-7B":
        llm = "a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea"
    elif selected_model == "Llama2-13B":
        llm = "a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5"
    temperature = st.sidebar.slider(
        "temperature", min_value=0.01, max_value=5.0, value=0.1, step=0.01
    )
    top_p = st.sidebar.slider(
        "top_p", min_value=0.01, max_value=1.0, value=0.9, step=0.01
    )
    max_length = st.sidebar.slider(
        "max_length", min_value=32, max_value=128, value=120, step=8
    )
    st.button("Clear Chat History", on_click=clear_chat_history)

    st.divider()
    ### ---------- Setting up Grobid parameters ---------- ###
    st.markdown("# :book: GROBID Editor")
    if init_grobid():
        st.success("GROBID server is up and running!", icon="✅")
    else:
        st.warning(
            "GROBID server does not appear up and running, the connection to the server failed!",
            icon="⚠️",
        )
    st.markdown("## Highlights controllers")
    highlight_title = st.toggle(
        "Title", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_person_names = st.toggle(
        "Person Names", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_affiliations = st.toggle(
        "Affiliations", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_head = st.toggle(
        "Head of sections", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_sentences = st.toggle(
        "Sentences", value=False, disabled=not st.session_state["uploaded"]
    )
    highlight_paragraphs = st.toggle(
        "Paragraphs", value=False, disabled=not st.session_state["uploaded"]
    )
    highlight_notes = st.toggle(
        "Notes", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_formulas = st.toggle(
        "Formulas", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_figures = st.toggle(
        "Figures and tables", value=True, disabled=not st.session_state["uploaded"]
    )
    highlight_callout = st.toggle(
        "References citations in text",
        value=True,
        disabled=not st.session_state["uploaded"],
    )
    highlight_citations = st.toggle(
        "Citations", value=True, disabled=not st.session_state["uploaded"]
    )

    st.header("Display options")
    annotation_thickness = st.slider(
        label="Annotation boxes border thickness", min_value=1, max_value=6, value=1
    )
    pages_vertical_spacing = st.slider(
        label="Pages vertical spacing", min_value=0, max_value=10, value=2
    )

    st.header("Height and width")
    width = st.slider(label="PDF width", min_value=100, max_value=1000, value=700)
    height = st.slider(label="PDF height", min_value=-1, max_value=10000, value=-1)

    st.header("Page Selection")
    placeholder = st.empty()

    if not st.session_state["pages"]:
        st.session_state["page_selection"] = placeholder.multiselect(
            "Select pages to display",
            options=[],
            default=[],
            help="The page number considered is the PDF number and not the document page number.",
            disabled=not st.session_state["pages"],
            key=1,
        )

    st.header("Documentation")
    st.markdown("https://github.com/ifatwme/paperx")
    st.markdown(
        """Upload a scientific article as PDF document and see the structures that are extracted by Grobid"""
    )

    if st.session_state["git_rev"] != "unknown":
        st.markdown(
            "**Revision number**: ["
            + st.session_state["git_rev"]
            + "](https://github.com/lfoppiano/structure-vision/commit/"
            + st.session_state["git_rev"]
            + ")"
        )


### ---------- Main Body ---------- ###
st.markdown("# Welcome to PaperX :newspaper: :x:")
st.markdown("### where you can eXplore even more!")
st.divider()

right_column, middle_column, left_column = st.columns(3, gap="small")


with right_column:
    uploaded_file = st.file_uploader(
        "Upload an article",
        type=("pdf"),
        on_change=new_file,
        help="The full-text is extracted using Grobid. ",
    )

    if uploaded_file:
        if not st.session_state["binary"]:
            with st.spinner("Reading file, calling Grobid..."):
                binary = uploaded_file.getvalue()
                tmp_file = NamedTemporaryFile()
                tmp_file.write(bytearray(binary))
                st.session_state["binary"] = binary
                annotations, pages = init_grobid().process_structure(tmp_file.name)

                st.session_state["annotations"] = (
                    annotations
                    if not st.session_state["annotations"]
                    else st.session_state["annotations"]
                )
                st.session_state["pages"] = (
                    pages
                    if not st.session_state["pages"]
                    else st.session_state["pages"]
                )

        if st.session_state["pages"]:
            st.session_state["page_selection"] = placeholder.multiselect(
                "Select pages to display",
                options=list(range(1, st.session_state["pages"])),
                default=[],
                help="The page number considered is the PDF number and not the document page number.",
                disabled=not st.session_state["pages"],
                key=2,
            )

        with st.spinner("Rendering PDF document"):
            annotations = st.session_state["annotations"]

            titles_list = [
                "s",
                "p",
                "title",
                "head",
                "biblStruct",
                "note",
                "ref",
                "formula",
                "persName",
                "figure",
            ]

            if not highlight_sentences:
                annotations = list(filter(lambda a: a["type"] != "s", annotations))

            if not highlight_paragraphs:
                annotations = list(filter(lambda a: a["type"] != "p", annotations))

            if not highlight_title:
                annotations = list(filter(lambda a: a["type"] != "title", annotations))

            if not highlight_head:
                annotations = list(filter(lambda a: a["type"] != "head", annotations))

            if not highlight_citations:
                annotations = list(
                    filter(lambda a: a["type"] != "biblStruct", annotations)
                )

            if not highlight_notes:
                annotations = list(filter(lambda a: a["type"] != "note", annotations))

            if not highlight_callout:
                annotations = list(filter(lambda a: a["type"] != "ref", annotations))

            if not highlight_formulas:
                annotations = list(
                    filter(lambda a: a["type"] != "formula", annotations)
                )

            if not highlight_person_names:
                annotations = list(
                    filter(lambda a: a["type"] != "persName", annotations)
                )

            if not highlight_figures:
                annotations = list(filter(lambda a: a["type"] != "figure", annotations))

            if not highlight_affiliations:
                annotations = list(
                    filter(lambda a: a["type"] != "affiliation", annotations)
                )

            if height > -1:
                pdf_viewer(
                    input=st.session_state["binary"],
                    width=width,
                    height=height,
                    annotations=annotations,
                    pages_vertical_spacing=pages_vertical_spacing,
                    annotation_outline_size=annotation_thickness,
                    pages_to_render=st.session_state["page_selection"],
                )
            else:
                pdf_viewer(
                    input=st.session_state["binary"],
                    width=width,
                    annotations=annotations,
                    pages_vertical_spacing=pages_vertical_spacing,
                    annotation_outline_size=annotation_thickness,
                    pages_to_render=st.session_state["page_selection"],
                )


with middle_column:
    st.markdown("### Here you can get your segments")
    if uploaded_file:
        filtered_sorted_segments = [
            {k: d[k] for k in ("type", "text")}
            for d in sorted(annotations, key=lambda x: x["type"])
        ]
        segments = [
            segment
            for segment in filtered_sorted_segments
            if len(str(segment["text"]).strip()) > 5
        ]
        st.session_state["segments"] = (
            segments
            if not st.session_state["segments"]
            else st.session_state["segments"]
        )
        labels = set()
        with st.spinner("Creating options..."):
            type_title = ""
            for segment in st.session_state["segments"]:
                label = str(segment["text"]).strip()
                if not (label in labels):
                    labels.add(label)
                    if segment["type"] != type_title:
                        st.markdown(f'### {segment["type"]}')
                        type_title = segment["type"]
                    try:
                        st.button(
                            label,
                            on_click=partial(
                                llama_write_answer,
                                prompt=f"give technical explanation about this topic: \n{label}",
                            ),
                        )
                    except Exception as e:
                        print(f"Error for {segment}, exception is: {e}")


with left_column:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    if prompt := st.chat_input(
        placeholder="Ask a question", max_chars=300, disabled=not replicate_api
    ):
        write_prompt(prompt)

    llama_answer(prompt)
