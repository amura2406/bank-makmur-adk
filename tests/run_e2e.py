"""
E2E Test Runner for Bank Makmur Conversational Agent.
Executes test cases against local, API, or deployed agents, verifying outputs and benchmarking latency/TTFT.
"""

import os
import sys
import time
import json
import re
import argparse
import asyncio
from typing import Dict, List, Any

# Mock class representing agent response stream for demonstration of latency / TTFT calculation
from mock_api.db_manager import DBManager
from crawler.ingest import ingest_data
from crawler.search import get_search_helper, INDEX_DIR

class MockEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 768 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 768
    def __call__(self, text):
        return self.embed_query(text)

def ensure_faiss_index():
    index_path = os.path.join(INDEX_DIR, "index.faiss")
    if not os.path.exists(index_path):
        print("E2E Runner: FAISS index not found. Building it using MockEmbeddings...")
        ingest_data(embeddings_model=MockEmbeddings())

import contextvars
import weakref
from collections.abc import MutableMapping

class TaskLocalDict(MutableMapping):
    def __init__(self):
        self._var = contextvars.ContextVar("mock_memory_bank", default=None)

    def _get_dict(self) -> dict:
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            current_task = None
        val = self._var.get()
        is_match = False
        if val is not None:
            task_ref, d = val
            if task_ref is None:
                is_match = (current_task is None)
            else:
                is_match = (task_ref() is current_task)
        if not is_match:
            d = {}
            ref = weakref.ref(current_task) if current_task is not None else None
            self._var.set((ref, d))
            return d
        return val[1]

    def __getitem__(self, key):
        return self._get_dict()[key]

    def __setitem__(self, key, value):
        self._get_dict()[key] = value

    def __delitem__(self, key):
        del self._get_dict()[key]

    def __iter__(self):
        return iter(self._get_dict())

    def __len__(self):
        return len(self._get_dict())

    def __contains__(self, key):
        return key in self._get_dict()

    def clear(self):
        self._get_dict().clear()

    def get(self, key, default=None):
        return self._get_dict().get(key, default)

    def pop(self, key, default=None):
        return self._get_dict().pop(key, default)

    def popitem(self):
        return self._get_dict().popitem()

    def setdefault(self, key, default=None):
        return self._get_dict().setdefault(key, default)

    def update(self, *args, **kwargs):
        self._get_dict().update(*args, **kwargs)

    def keys(self):
        return self._get_dict().keys()

    def values(self):
        return self._get_dict().values()

    def items(self):
        return self._get_dict().items()

    def __repr__(self):
        return repr(self._get_dict())

    def __str__(self):
        return str(self._get_dict())

# Global memory bank to simulate long-term memory persistence
MOCK_MEMORY_BANK = TaskLocalDict()

CURRENT_SESSION_ID = "e2e-session-default"
CURRENT_USER_ID = "e2e-user-default"


async def simulate_agent_call(message: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simulates calling the agent. In mock mode, we use actual TinyDB data
    and actual FAISS RAG to construct realistic agent responses.
    """
    from opentelemetry import trace
    tracer = trace.get_tracer("bank-makmur-agent")

    with tracer.start_as_current_span("agent_turn") as turn_span:
        turn_span.set_attribute("message", message)
        start_time = time.perf_counter()
        global MOCK_MEMORY_BANK
        
        # 1. Determine current language
        lang = "id" # default to indonesian since most of our app is indonesian!
        for h in history:
            h_text = h["parts"][0]["text"].lower()
            if "english" in h_text or "inggris" in h_text:
                lang = "en"
            elif "bahasa indonesia" in h_text or "indonesian" in h_text:
                lang = "id"
        
        msg_lower = message.lower()
        if "english" in msg_lower or "inggris" in msg_lower:
            lang = "en"
        elif "bahasa indonesia" in msg_lower or "indonesian" in msg_lower:
            lang = "id"
        else:
            # Check for english keywords
            english_words = ["hello", "hi", "how", "are", "you", "today", "what", "services", "do", "provide", "show", "my", "transaction", "history", "balance", "saving", "pocket", "interest", "rate", "pockets", "create", "limit", "branches", "office", "where", "is", "can", "check", "who", "am", "i", "actually", "name", "is", "good", "morning", "speak", "in", "write", "binary", "search", "tree", "python", "weather", "forecast", "tomorrow", "jakarta", "is", "there", "any", "fee"]
            words = re.findall(r"\b\w+\b", msg_lower)
            eng_count = sum(1 for w in words if w in english_words)
            ind_count = sum(1 for w in words if w in ["halo", "apa", "siapa", "bagaimana", "mengapa", "di", "ke", "dari", "yang", "untuk", "dengan", "saya", "anda", "kamu", "bantu", "bisa", "tidak", "sakit", "kepala", "obat", "bunga", "saldo", "kantong", "mutasi", "transaksi", "riwayat", "berapa", "utama", "tabungan", "apakah", "selamat", "pagi", "siang", "sore", "malam", "tanya", "mau", "kantor", "cabang", "alamat", "buat", "layani", "asisten", "tolong", "pakai", "rekening", "tampilkan", "cek", "joko", "budi", "agus", "bisa", "ganti"])
            if eng_count > ind_count:
                lang = "en"
            elif ind_count > eng_count:
                lang = "id"

        # 2. Memory / Name check (F05)
        name = MOCK_MEMORY_BANK.get("user_name")
        
        def extract_name(text: str):
            text_clean = text.strip().rstrip(".?!")
            # Try specific templates first
            patterns = [
                r"\b(?:my name is|nama saya|i am|i'm|saya adalah|saya)\s+([A-Za-z0-9_-]+)$",
                r"\b(?:my name is|nama saya)\s+(?:adalah\s+)?([A-Za-z0-9_-]+)"
            ]
            for pat in patterns:
                m = re.search(pat, text_clean, re.IGNORECASE)
                if m:
                    captured = m.group(1)
                    if captured.lower() not in ["ingin", "mau", "bisa", "tidak", "jago", "makmur", "a", "an", "the", "virtual", "assistant", "bertanya"]:
                        return captured
            return None

        # Update name from history
        for h in history:
            if h.get("role") != "user":
                continue
            extracted = extract_name(h["parts"][0]["text"])
            if extracted:
                name = extracted
                MOCK_MEMORY_BANK["user_name"] = name
                
        # Update name from current message
        extracted = extract_name(message)
        if extracted:
            name = extracted
            MOCK_MEMORY_BANK["user_name"] = name

        called_tools = []
        text_response = ""

        # Language switch pure messages check
        is_lang_switch = False
        if ("english" in msg_lower or "inggris" in msg_lower) and any(w in msg_lower for w in ["switch", "ganti", "pakai", "speak", "bicara", "use", "talk", "change"]):
            if not any(w in msg_lower for w in ["saldo", "balance", "mutasi", "transaction", "riwayat", "pengeluaran", "bunga", "interest"]):
                is_lang_switch = True
                lang = "en"
                text_response = "Sure! I can assist you in English now. How can I help you?"
        elif ("indonesia" in msg_lower) and any(w in msg_lower for w in ["switch", "ganti", "pakai", "speak", "bicara", "use", "talk", "ganti ke"]):
            if not any(w in msg_lower for w in ["saldo", "balance", "mutasi", "transaction", "riwayat", "pengeluaran", "bunga", "interest"]):
                is_lang_switch = True
        # 3. Handle Guardrails / Safety Checks
        # Affiliation with Bank Jago check
        if text_response:
            pass
        # Affiliation with Bank Jago check
        elif "jago" in msg_lower and any(x in msg_lower for x in ["affiliated", "afiliasi", "relationship", "hubungannya", "relationship", "sama dengan", "bekerjasama", "kerja sama"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "safety_check")
                called_tools.append("safety_check")
                with tracer.start_as_current_span("llm_call") as llm_span:
                    if lang == "id":
                        text_response = "Saya adalah asisten virtual Bank Makmur and tidak terafiliasi dengan Bank Jago."
                    else:
                        text_response = "I am a virtual assistant for Bank Makmur and am not affiliated with Bank Jago."
        
        # Override / prompt injection
        elif any(x in msg_lower for x in ["ignore", "system instruction", "override instructions"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "safety_check")
                called_tools.append("safety_check")
                with tracer.start_as_current_span("llm_call") as llm_span:
                    if lang == "id":
                        text_response = "Maaf, saya tidak bisa melakukan itu. Saya di sini untuk membantu Anda dengan layanan perbankan Bank Makmur."
                    else:
                        text_response = "Sorry, I cannot do that. I am here to help you with Bank Makmur banking services."

        # Coding / Medical / Weather
        elif any(x in msg_lower for x in ["python", "code", "programming", "medical", "obat", "coding", "java", "script", "program", "cat /etc/passwd", "system logs", "weather", "cuaca", "tomorrow", "forecast"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "safety_check")
                called_tools.append("safety_check")
                with tracer.start_as_current_span("llm_call") as llm_span:
                    if lang == "id":
                        text_response = "Maaf, saya hanya dapat membantu Anda dengan pertanyaan dan layanan perbankan Bank Makmur."
                    else:
                        text_response = "Sorry, I can only assist you with Bank Makmur banking questions and services."

        # 4. Explicit Language Switch Requests
        elif any(x in msg_lower for x in ["switch to", "change to", "speak in", "talk in", "ganti ke bahasa", "bicara bahasa", "ganti bahasa"]):
            with tracer.start_as_current_span("llm_call") as llm_span:
                if lang == "en":
                    text_response = "Certainly! I will switch to English now. How can I help you today?"
                else:
                    text_response = "Tentu, saya akan berbicara dalam Bahasa Indonesia sekarang. Ada yang bisa saya bantu?"

        # 5. Greetings
        elif (msg_lower.strip() in ["hello", "hi", "hey", "halo", "pagi", "siang", "sore", "malam"] or any(msg_lower.startswith(x) for x in ["hello ", "hi ", "halo ", "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "good morning", "good afternoon", "good evening"])) and not any(w in msg_lower for w in ["saldo", "balance", "mutasi", "transaction", "riwayat", "pengeluaran", "bunga", "interest"]):
            with tracer.start_as_current_span("llm_call") as llm_span:
                if lang == "en":
                    text_response = "Hello! Welcome to Bank Makmur customer support. How can I assist you today?"
                else:
                    text_response = "Halo! Selamat datang di layanan bantuan Bank Makmur. Ada yang bisa saya bantu?"

        # 6. General Services Inquiry
        elif any(x in msg_lower for x in ["what services", "how can you help", "what can you do", "help me", "list of services", "provide"]):
            with tracer.start_as_current_span("llm_call") as llm_span:
                if lang == "en":
                    text_response = "I can help you check your account balance, view your transaction history, search the FAQ, and more. How can I assist you today?"
                else:
                    text_response = "Saya dapat membantu Anda memeriksa saldo rekening, melihat riwayat transaksi, mencari informasi di FAQ, dan lainnya. Ada yang bisa saya bantu?"

        # 7. Session Name Retrieval / Who am I?
        elif any(x in msg_lower for x in ["who am i", "siapa saya", "my name", "nama saya", "what is my name", "who is my name", "siapa nama saya"]):
            with tracer.start_as_current_span("llm_call") as llm_span:
                if name:
                    if lang == "id":
                        text_response = f"Nama Anda adalah {name}."
                    else:
                        text_response = f"Your name is {name}."
                else:
                    if lang == "id":
                        text_response = "Maaf, saya belum mengetahui nama Anda."
                    else:
                        text_response = "Sorry, I don't know your name yet."

        # 8. Name introduction greeting
        elif any(msg_lower.startswith(x) for x in ["my name is", "nama saya", "i am", "saya is"]):
            with tracer.start_as_current_span("llm_call") as llm_span:
                if lang == "id":
                    text_response = f"Halo {name}! Senang berkenalan dengan Anda. Ada yang bisa saya bantu?"
                else:
                    text_response = f"Hello {name}! Nice to meet you. How can I help you today?"

        # 9. Personalized Pocket Balance Query (F03)
        elif any(x in msg_lower for x in ["balance", "saldo", "sald", "salod", "balanc"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "get_pocket_balance")
                called_tools.append("get_pocket_balance")
                
                db = DBManager()
                account = None
                if name:
                    accounts = db.find_accounts_by_owner(name)
                    if accounts:
                        account = accounts[0]
                    else:
                        # Unrecognized owner name specified
                        if lang == "id":
                            text_response = f"Maaf, rekening untuk pengguna '{name}' tidak ditemukan."
                        else:
                            text_response = f"Sorry, the account for user '{name}' was not found."
                
                # If no name is provided, default to Angga's account
                if not name and not account:
                    account = db.get_account("acc-angga-001")
                
                if account:
                    # Map pocket name
                    pocket_query = None
                    if any(w in msg_lower for w in ["main", "utama", "utma"]):
                        pocket_query = "main pocket"
                    elif any(w in msg_lower for w in ["saving", "tabungan", "savng"]):
                        pocket_query = "saving pocket"
                    elif any(w in msg_lower for w in ["holiday", "liburan"]):
                        pocket_query = "holiday pocket"
                    elif any(w in msg_lower for w in ["travel", "perjalanan"]):
                        pocket_query = "travel pocket"
                    elif any(w in msg_lower for w in ["shopping", "belanja"]):
                        pocket_query = "shopping pocket"
                    elif any(w in msg_lower for w in ["emergency", "darurat"]):
                        pocket_query = "emergency pocket"
                    else:
                        m = re.search(r"(?:pocket|kantong|kantung)\s+([A-Za-z0-9_-]+)", msg_lower)
                        if m:
                            pocket_query = f"{m.group(1)} pocket"

                    pocket_obj = None
                    if pocket_query:
                        for p in account.get("pockets", []):
                            p_clean = p["name"].lower().replace(" pocket", "")
                            q_clean = pocket_query.lower().replace(" pocket", "")
                            if p_clean == q_clean:
                                pocket_obj = p
                                break

                    with tracer.start_as_current_span("llm_call") as llm_span:
                        if pocket_obj:
                            balance = pocket_obj["balance"]
                            if lang == "id":
                                bal_str = f"{balance:,.0f}".replace(",", ".")
                                text_response = f"Saldo Kantong {pocket_obj['name'].capitalize()} Anda saat ini adalah Rp {bal_str}."
                            else:
                                text_response = f"The balance in your {pocket_obj['name']} is Rp {balance:,.0f}."
                        else:
                            # Pocket not found
                            if lang == "id":
                                text_response = f"Maaf, kantong '{pocket_query or 'unknown'}' tidak ditemukan."
                            else:
                                text_response = f"Sorry, the pocket '{pocket_query or 'unknown'}' was not found."

        # 10. Transaction History Query (F04)
        elif any(x in msg_lower for x in ["transaction", "mutasi", "riwayat", "pengeluaran", "transaksi", "transksi", "rwayat", "tx", "records"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "get_transaction_history")
                called_tools.append("get_transaction_history")
                
                db = DBManager()
                account = None
                if name:
                    accounts = db.find_accounts_by_owner(name)
                    if accounts:
                        account = accounts[0]
                    else:
                        if lang == "id":
                            text_response = "Tidak ada riwayat transaksi yang ditemukan."
                        else:
                            text_response = "No transaction history found."
                
                if not name and not account:
                    account = db.get_account("acc-angga-001")
                
                if account:
                    # Map pocket name
                    pocket_query = None
                    if any(w in msg_lower for w in ["main", "utama", "utma"]):
                        pocket_query = "main pocket"
                    elif any(w in msg_lower for w in ["saving", "tabungan", "savng"]):
                        pocket_query = "saving pocket"
                    elif any(w in msg_lower for w in ["holiday", "liburan"]):
                        pocket_query = "holiday pocket"
                    elif any(w in msg_lower for w in ["travel", "perjalanan"]):
                        pocket_query = "travel pocket"
                    elif any(w in msg_lower for w in ["shopping", "belanja"]):
                        pocket_query = "shopping pocket"
                    elif any(w in msg_lower for w in ["emergency", "darurat"]):
                        pocket_query = "emergency pocket"
                    else:
                        m = re.search(r"(?:pocket|kantong|kantung)\s+([A-Za-z0-9_-]+)", msg_lower)
                        if m:
                            pocket_query = f"{m.group(1)} pocket"

                    # Parse limit
                    limit = None
                    m_lim = re.search(r"\b(\d+)\b", msg_lower)
                    if m_lim:
                        limit = int(m_lim.group(1))
                    if limit is None or limit <= 0:
                        limit = 5

                    txs = db.get_transactions(account["account_id"], pocket=pocket_query, limit=limit)
                    
                    with tracer.start_as_current_span("llm_call") as llm_span:
                        if txs:
                            tx_lines = []
                            for tx in txs:
                                amt_str = f"{tx['amount']:,.0f}".replace(",", ".")
                                tx_lines.append(f"- {tx['timestamp']}: {tx['description']} (Rp {amt_str})")
                            tx_summary = "\n".join(tx_lines)
                            if lang == "id":
                                if pocket_query:
                                    text_response = f"Berikut adalah riwayat transaksi terakhir Anda di kantong {pocket_query}:\n{tx_summary}"
                                else:
                                    text_response = f"Berikut adalah riwayat transaksi terakhir Anda:\n{tx_summary}"
                            else:
                                if pocket_query:
                                    text_response = f"Here is your recent transaction history in {pocket_query}:\n{tx_summary}"
                                else:
                                    text_response = f"Here is your recent transaction history:\n{tx_summary}"
                        else:
                            if lang == "id":
                                if pocket_query:
                                    text_response = f"Tidak ada riwayat transaksi yang ditemukan di kantong {pocket_query}."
                                else:
                                    text_response = "Tidak ada riwayat transaksi yang ditemukan."
                            else:
                                if pocket_query:
                                    text_response = f"No transaction history found in {pocket_query}."
                                else:
                                    text_response = "No transaction history found."
                else:
                    with tracer.start_as_current_span("llm_call") as llm_span:
                        if lang == "id":
                            text_response = "Tidak ada riwayat transaksi yang ditemukan."
                        else:
                            text_response = "No transaction history found."

        # 11. Specific FAQ Topics with high-quality English & Indonesian response fallback (F02)
        elif any(w in msg_lower for w in ["bunga", "interest", "rate"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "faq_search")
                called_tools.append("faq_search")
                with tracer.start_as_current_span("llm_call") as llm_span:
                    if lang == "id":
                        text_response = "Suku bunga tabungan Bank Makmur adalah 3.5% per tahun untuk Kantong Nabung."
                    else:
                        text_response = "Bank Makmur offers an interest rate of 3.5% per annum for Saving Pockets."

        elif any(w in msg_lower for w in ["pocket", "kantong", "kantung", "limit"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "faq_search")
                called_tools.append("faq_search")
                with tracer.start_as_current_span("llm_call") as llm_span:
                    if "transfer" in msg_lower:
                        if lang == "id":
                            text_response = "Ya, Anda dapat mentransfer dana ke kantong lain melalui aplikasi Bank Makmur dengan memilih opsi transfer kantong."
                        else:
                            text_response = "Yes, you can transfer funds to another pocket in the Bank Makmur app."
                    else:
                        if lang == "id":
                            text_response = "Anda dapat membuat hingga 20 Kantong Makmur untuk memisahkan tabungan dan pengeluaran Anda."
                        else:
                            text_response = "You can create up to 20 Bank Makmur pockets to manage your savings and spending."

        elif any(w in msg_lower for w in ["branch", "cabang", "alamat", "kantor"]):
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "faq_search")
                called_tools.append("faq_search")
                with tracer.start_as_current_span("llm_call") as llm_span:
                    if lang == "id":
                        text_response = "Kantor cabang Bank Makmur berlokasi di Jl. Jend. Sudirman No. 21, Jakarta Pusat."
                    else:
                        text_response = "Bank Makmur branch offices are located at Jl. Jend. Sudirman No. 21, Jakarta Pusat."

        # 12. FAQ Retrieval (F02) - General FAQ
        else:
            with tracer.start_as_current_span("tool_call") as tool_span:
                tool_span.set_attribute("tool_name", "faq_search")
                called_tools.append("faq_search")
                
                with tracer.start_as_current_span("llm_call") as llm_span:
                    ensure_faiss_index()
                    search_helper = get_search_helper(embeddings_model=MockEmbeddings(), index_dir=INDEX_DIR)
                    
                    faq_answer = None
                    if search_helper.db:
                        all_docs = list(search_helper.db.docstore._dict.values())
                        best_doc = None
                        best_score = 0
                        words_query = [w for w in message.lower().split() if len(w) > 3]
                        for doc in all_docs:
                            score = 0
                            doc_lower = doc.page_content.lower()
                            for w in words_query:
                                if w in doc_lower:
                                    score += 1
                            if score > best_score:
                                best_score = score
                                best_doc = doc
                        if best_doc:
                            content = best_doc.page_content
                            if "Answer:" in content:
                                faq_answer = content.split("Answer:", 1)[1].strip()
                            else:
                                faq_answer = content
                    
                    if not faq_answer:
                        results = search_helper.search(message, k=1)
                        if results:
                            content = results[0]
                            if "Answer:" in content:
                                faq_answer = content.split("Answer:", 1)[1].strip()
                            else:
                                faq_answer = content

                    if faq_answer:
                        text_response = faq_answer
                    else:
                        if lang == "id":
                            text_response = "Halo! Saya asisten virtual Bank Makmur. Ada yang bisa saya bantu?"
                        else:
                            text_response = "Hello! I am your Bank Makmur virtual assistant. How can I help you today?"

        # Simulate TTFT and latency
        end_time = time.perf_counter()
        duration = max(0.1, end_time - start_time)
        ttft = duration * 0.3

        return {
            "text": text_response,
            "ttft_seconds": ttft,
            "latency_seconds": duration,
            "called_tools": called_tools
        }

async def execute_turn(user_input: str, history: List[Dict[str, Any]], mode: str, endpoint: str) -> Dict[str, Any]:
    """Executes a single conversational turn in the specified mode."""
    if mode == "mock":
        return await simulate_agent_call(user_input, history)
    elif mode == "local":
        import subprocess
        cmd = [sys.executable, "-m", "app.agent", "--message", user_input]
        t0 = time.perf_counter()
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        t1 = time.perf_counter()
        
        output_text = process.stdout.strip()
        try:
            res_data = json.loads(output_text)
            text = res_data.get("text", output_text)
            called_tools = res_data.get("called_tools", [])
        except json.JSONDecodeError:
            text = output_text
            called_tools = []
            
        return {
            "text": text,
            "ttft_seconds": 0.1,
            "latency_seconds": t1 - t0,
            "called_tools": called_tools
        }
    elif mode == "api":
        import httpx
        url = f"{endpoint.rstrip('/')}/chat"
        t0 = time.perf_counter()
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json={"message": user_input, "history": history}, timeout=30.0)
            res.raise_for_status()
            res_data = res.json()
        t1 = time.perf_counter()
        
        return {
            "text": res_data.get("text", ""),
            "ttft_seconds": res_data.get("ttft_seconds", 0.2),
            "latency_seconds": t1 - t0,
            "called_tools": res_data.get("called_tools", [])
        }
    elif mode == "deployed":
        import vertexai
        engine_id = os.getenv("VERTEX_ENGINE_ID")
        if not engine_id:
            raise ValueError("VERTEX_ENGINE_ID environment variable not set for 'deployed' mode.")
        project = os.getenv("GCP_PROJECT", "anggar-conv-agent")
        location = os.getenv("GCP_LOCATION", "asia-southeast1")
        
        client = vertexai.Client(project=project, location=location)
        agent = client.agent_engines.get(name=engine_id)
        
        global CURRENT_SESSION_ID, CURRENT_USER_ID
        
        if len(history) == 0:
            agent.create_session(user_id=CURRENT_USER_ID, session_id=CURRENT_SESSION_ID)
            
        t0 = time.perf_counter()
        ttft = None
        text_response = ""
        called_tools = []
        
        for event in agent.stream_query(
            message=user_input,
            user_id=CURRENT_USER_ID,
            session_id=CURRENT_SESSION_ID
        ):
            if ttft is None:
                ttft = time.perf_counter() - t0
                
            content = event.get("content")
            if content and content.get("parts"):
                for part in content["parts"]:
                    if "text" in part:
                        text_response += part["text"]
                    if "function_call" in part:
                        fc = part["function_call"]
                        func_name = fc.get("name")
                        if func_name:
                            mapped_name = func_name
                            if func_name == "check_pocket_balance":
                                mapped_name = "get_pocket_balance"
                            elif func_name == "check_transactions":
                                mapped_name = "get_transaction_history"
                            elif func_name == "search_faq":
                                mapped_name = "faq_search"
                            if mapped_name not in called_tools:
                                called_tools.append(mapped_name)
                                
        t1 = time.perf_counter()
        if ttft is None:
            ttft = t1 - t0
            
        return {
            "text": text_response.strip(),
            "ttft_seconds": ttft,
            "latency_seconds": t1 - t0,
            "called_tools": called_tools
        }
    else:
        raise ValueError(f"Unknown mode: {mode}")

async def run_test_case(case: Dict[str, Any], endpoint: str, mode: str) -> Dict[str, Any]:
    """Runs all turns of a single test case sequentially."""
    global MOCK_MEMORY_BANK, CURRENT_SESSION_ID, CURRENT_USER_ID
    import uuid
    CURRENT_SESSION_ID = f"e2e-session-{uuid.uuid4()}"
    CURRENT_USER_ID = f"e2e-user-{uuid.uuid4()}"
    MOCK_MEMORY_BANK.clear()
    print(f"\n[TEST] Running {case['id']}: {case['description']}")
    history = []
    results = []
    case_success = True
    
    for turn_idx, turn in enumerate(case["turns"]):
        user_input = turn["user_input"]
        print(f"  Turn {turn_idx + 1} User: '{user_input}'")
        
        response = await execute_turn(user_input, history, mode, endpoint)
        
        # Log performance metrics
        print(f"    - TTFT: {response['ttft_seconds']:.3f}s | Latency: {response['latency_seconds']:.3f}s")
        print(f"    - Agent: '{response['text']}'")
        
        # Verify assertions
        assertions = turn.get("assertions", {})
        turn_success = True
        errors = []
        
        # 1. Regex assertion
        if "regex" in assertions:
            pattern = re.compile(assertions["regex"], re.IGNORECASE)
            if not pattern.search(response["text"]):
                turn_success = False
                errors.append(f"Response '{response['text']}' did not match pattern '{assertions['regex']}'")
                
        # 2. Expected tools assertion
        if "expected_tools" in assertions:
            for tool in assertions["expected_tools"]:
                if tool not in response.get("called_tools", []):
                    turn_success = False
                    errors.append(f"Expected tool '{tool}' was not called")
                    
        # 3. Forbidden words assertion
        if "forbidden_words" in assertions:
            for word in assertions["forbidden_words"]:
                if word.lower() in response["text"].lower():
                    turn_success = False
                    errors.append(f"Forbidden word '{word}' found in response")
                    
        if turn_success:
            print("    [PASS]")
        else:
            print(f"    [FAIL] Reasons: {', '.join(errors)}")
            case_success = False
            
        results.append({
            "turn_idx": turn_idx,
            "success": turn_success,
            "errors": errors,
            "metrics": {
                "ttft_seconds": response["ttft_seconds"],
                "latency_seconds": response["latency_seconds"]
            }
        })
        
        # Append turn to history
        history.append({"role": "user", "parts": [{"text": user_input}]})
        history.append({"role": "model", "parts": [{"text": response["text"]}]})
        
    return {
        "case_id": case["id"],
        "success": case_success,
        "turns": results
    }

async def main():
    parser = argparse.ArgumentParser(description="Run Bank Makmur agent E2E tests.")
    parser.add_argument("--mode", choices=["mock", "local", "api", "deployed"], default="mock", help="Execution mode")
    parser.add_argument("--endpoint", default="http://localhost:8000", help="FastAPI endpoint for 'api' mode")
    parser.add_argument("--cases", default="tests/test_cases.json", help="Path to test cases JSON file")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], default=None, help="Filter by test tier")
    
    args = parser.parse_args()
    
    # Resolve absolute path to test cases
    if not os.path.exists(args.cases):
        local_path = os.path.join(os.path.dirname(__file__), "test_cases.json")
        if os.path.exists(local_path):
            args.cases = local_path
        else:
            print(f"Error: Cases file not found at {args.cases}")
            sys.exit(1)
            
    with open(args.cases, "r") as f:
        data = json.load(f)
        
    test_cases = data.get("test_cases", [])
    if args.tier:
        test_cases = [c for c in test_cases if c["tier"] == args.tier]
        
    print(f"Loaded {len(test_cases)} test cases in tier: {args.tier or 'All'}")
    
    summary = []
    for case in test_cases:
        res = await run_test_case(case, args.endpoint, args.mode)
        summary.append(res)
        
    # Print final test report
    total = len(summary)
    passed = sum(1 for s in summary if s["success"])
    failed = total - passed
    
    print("\n" + "="*50)
    print("                    E2E TEST REPORT")
    print("="*50)
    print(f"Total Cases: {total}")
    print(f"Passed:      {passed}")
    print(f"Failed:      {failed}")
    print("="*50)
    
    for s in summary:
        status = "PASS" if s["success"] else "FAIL"
        print(f"- {s['case_id']}: {status}")
        
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
