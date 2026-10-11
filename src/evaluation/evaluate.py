import time
import os
import json
import re

from rag import retrieve, build_context, generate
from config import (EVAL_OUTPUT_PATH, EVAL_TOP_K, BENCHMARK_QUESTIONS)

def compute_retrieval_metrics(
    results, 
    expected_cis, 
    expected_denomination,
    expected_section, 
    top_k
):
    """
    Calcule Hit@k, Precision@k et MRR.
    Un chunk est valide s'il a la bonne section ET (le bon CIS ou la bonne molécule).
    """
    docs = results.get("documents", [[]])
    if not docs or not docs[0]:
        return {"hit_at_k": 0.0, "precision_at_k": 0.0, "mrr": 0.0, "nb_retrieved": 0}

    metadatas = results.get("metadatas", [[]])[0][:top_k]
    
    target_cis = []
    if isinstance(expected_cis, str) and expected_cis:
        target_cis = [expected_cis.strip()]
    elif isinstance(expected_cis, list):
        target_cis = [str(c).strip() for c in expected_cis if c]

    target_sec = str(expected_section).strip().lower() if expected_section else ""
    target_denom = str(expected_denomination).strip().lower() if expected_denomination else ""

    correct_ranks = []
    relevant_count = 0

    for rank, meta in enumerate(metadatas, start=1):
        chunk_sec = str(meta.get("section", "")).strip().lower()
        chunk_cis = str(meta.get("CIS", "")).strip()
        chunk_denom = str(meta.get("denomination", "")).strip().lower()
        chunk_subst = str(meta.get("substance_active", "")).strip().lower()

        # 1. Validation de la section
        match_section = (chunk_sec == target_sec)

        match_cis = (chunk_cis in target_cis) if target_cis else False
        match_denom = (target_denom in chunk_denom or 
                       target_denom in chunk_subst or 
                       any(target_denom in s for s in chunk_subst.split(","))) if target_denom else False

        match_substance = match_cis or match_denom

        if match_section and match_substance :
            relevant_count += 1
            correct_ranks.append(rank)
    
    hit_at_k = 1.0 if len(correct_ranks) > 0 else 0.0
    precision_at_k = round(relevant_count / top_k, 4) if top_k > 0 else 0.0
    mrr = round(1.0 / correct_ranks[0], 4) if correct_ranks else 0.0

    return {
        "hit_at_k": hit_at_k,
        "precision_at_k": precision_at_k,
        "mrr": mrr,
        "nb_retrieved": len(metadatas)
    }


def compute_formal_compliance(
    response: str, 
    expected_denomination: str, 
    expected_section: str,
    context_is_empty: bool = False
) -> dict:
    """
    Vérification déterministe de la réponse : ancrage, traçabilité et refus sur contexte vide[cite: 1, 2].
    """
    if not response or not isinstance(response, str):
        return {
            "anchorage_nominal": False,
            "section_traceability": False,
            "uncertainty_handled": False,
            "len_words": 0
        }

    resp_clean = response.lower()

    # 1. Ancrage nominal (dénomination attendue présente)
    anchorage = (expected_denomination.lower() in resp_clean) if expected_denomination else False

    # 2. Traçabilité nosologique (ex: "4.3" ou "rubrique 4.3")
    sec_pattern = rf"(rubrique\s+)?{re.escape(str(expected_section))}"
    traceability = bool(re.search(sec_pattern, resp_clean)) if expected_section else False

    # 3. Gestion de l'incertitude (activée si contexte vide ou refus explicite)
    refusal_markers = [
        "je ne sais pas", 
        "documentation insuffisante", 
        "information non disponible", 
        "données insuffisantes",
        "ne permet pas de répondre"
    ]
    refusal_triggered = any(marker in resp_clean for marker in refusal_markers)
    uncertainty_ok = refusal_triggered if context_is_empty else True

    return {
        "anchorage_nominal": anchorage,
        "section_traceability": traceability,
        "uncertainty_handled": uncertainty_ok,
        "len_words": len(response.strip().split())
    }


def run_evaluation(questions: list[dict]) -> list[dict]:
    eval_results = []
    
    print("\n" + "=" * 70)
    print(f"🔬 DÉMARRAGE DU BENCHMARK PHARMARAG-FR ({len(questions)} QUESTIONS)")
    print("=" * 70)

    for q in questions:
        q_id = q["id"]
        query = q["query"]
        print(f"\n⏳ Traitement de [{q_id}] en cours...", end="", flush=True)
        top_k = q.get("top_k", EVAL_TOP_K)
        filtre_sec = q.get("filtre_section")
        exp_denom = q.get("expected_denomination", "")
        exp_sec = q.get("expected_section", "")
        exp_cis = q.get("expected_cis", [])

        # 1. Retrieval
        raw_retrieval = retrieve(query, top_k=top_k, filtre_section=filtre_sec)
        ret_metrics = compute_retrieval_metrics(
            results=raw_retrieval,
            expected_cis=exp_cis,
            expected_denomination=exp_denom,
            expected_section=exp_sec,
            top_k=top_k
        )

        # Vérification si le contexte extrait est vide
        docs = raw_retrieval.get("documents", [[]])
        context_empty = (not docs or not docs[0])

        # 2. Génération + chronométrage
        t_start = time.time()
        response_text = generate(query, top_k=top_k, filtre_section=filtre_sec)
        t_elapsed = round(time.time() - t_start, 2)

        # 3. Évaluation formelle
        gen_metrics = compute_formal_compliance(
            response=response_text,
            expected_denomination=exp_denom,
            expected_section=exp_sec,
            context_is_empty=context_empty
        )

        record = {
            "id": q_id,
            "query": query,
            "retrieval": ret_metrics,
            "generation": gen_metrics,
            "elapsed_time_sec": t_elapsed
        }
        eval_results.append(record)

        # Résumé par question dans le terminal
        print(f"\n▶ [{q_id}] {query[:60]}...")
        print(f"   Retrieval  : Hit@{top_k}={ret_metrics['hit_at_k']} | P@{top_k}={ret_metrics['precision_at_k']} | MRR={ret_metrics['mrr']}")
        print(f"   Génération : Ancrage={gen_metrics['anchorage_nominal']} | Traçabilité={gen_metrics['section_traceability']} | Temps={t_elapsed}s")

    # Calcul des moyennes globales
    n = len(eval_results)
    mean_hit = round(sum(r["retrieval"]["hit_at_k"] for r in eval_results) / n, 4)
    mean_prec = round(sum(r["retrieval"]["precision_at_k"] for r in eval_results) / n, 4)
    mean_mrr = round(sum(r["retrieval"]["mrr"] for r in eval_results) / n, 4)
    mean_time = round(sum(r["elapsed_time_sec"] for r in eval_results) / n, 2)

    print("\n" + "=" * 70)
    print("📊 RÉCAPITULATIF GLOBAL DU BENCHMARK")
    print("=" * 70)
    print(f"• Total questions évaluées : {n}")
    print(f"• Hit@k moyen              : {mean_hit * 100:.1f} %")
    print(f"• Precision@k moyenne      : {mean_prec * 100:.1f} %")
    print(f"• MRR moyen                : {mean_mrr}")
    print(f"• Temps moyen génération   : {mean_time} s")
    print("=" * 70)

    # Sauvegarde au format JSON Lines[cite: 1]
    os.makedirs(os.path.dirname(EVAL_OUTPUT_PATH), exist_ok=True)
    with open(EVAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for r in eval_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"💾 Résultats persistés dans : {EVAL_OUTPUT_PATH}\n")

    return eval_results



if __name__ == "__main__":
   run_evaluation(BENCHMARK_QUESTIONS)