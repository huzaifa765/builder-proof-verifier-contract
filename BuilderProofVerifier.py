# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import typing

class BuilderProofVerifier(gl.Contract):

    owner: str
    total_submissions: u256
    submissions: TreeMap[str, str]
    verdicts: TreeMap[str, str]

    def __init__(self) -> None:
        self.owner = str(gl.message.sender_address)
        self.total_submissions = u256(0)
        self.submissions = TreeMap()
        self.verdicts = TreeMap()

    @gl.public.write
    def submit_proof(
        self,
        proof_id: str,
        github_url: str,
        demo_url: str,
        summary: str
    ) -> None:
        if not proof_id or not summary:
            raise Exception("proof_id and summary are required")

        submission = json.dumps({
            "proof_id": proof_id,
            "github_url": github_url,
            "demo_url": demo_url,
            "summary": summary,
            "submitter": str(gl.message.sender_address),
            "status": "PENDING"
        })
        self.submissions[proof_id] = submission
        self.total_submissions = u256(int(self.total_submissions) + 1)

    @gl.public.write
    def judge_proof(self, proof_id: str) -> None:
        submission_raw = self.submissions.get(proof_id, "")
        if not submission_raw:
            raise Exception("Submission not found")

        submission = json.loads(submission_raw)

        def get_leader_result() -> str:
            web_data = ""
            if submission.get("github_url"):
                try:
                    response = gl.nondet.web.get(submission["github_url"])
                    web_data = response.body.decode("utf-8")[:1500]
                except:
                    web_data = "GitHub data unavailable"

            prompt = f"""You are an impartial GenLayer validator reviewing a builder proof submission.

Builder summary: {submission['summary']}
GitHub content: {web_data}

Based on this evidence, evaluate the submission and return ONLY valid JSON in this exact format with no extra text:
{{"verdict": "SHIPPED", "score": 80, "evidence_quality": "MEDIUM", "reasons": ["reason here"], "risk_flags": [], "confidence": "MEDIUM"}}

verdict must be one of: SHIPPED, WEAK, FAKE, NEEDS_MORE_EVIDENCE
score must be integer 0-100
evidence_quality must be: LOW, MEDIUM, or HIGH
confidence must be: LOW, MEDIUM, or HIGH"""

            return gl.nondet.exec_prompt(prompt)

        def validator_fn(leader_result: str) -> bool:
            prompt = f"""A GenLayer leader validator evaluated a builder proof and returned this result:
{leader_result}

The builder's summary was: {submission['summary']}

Is this verdict reasonable and fair based on the evidence? Reply with only the word: true or false"""
            
            output = gl.nondet.exec_prompt(prompt)
            return "true" in output.strip().lower()

        result = gl.eq_principle.nondet(get_leader_result, validator_fn)

        self.verdicts[proof_id] = json.dumps({
            "proof_id": proof_id,
            "verdict_raw": result,
            "judged": True
        })

    @gl.public.view
    def get_submission(self, proof_id: str) -> str:
        return self.submissions.get(proof_id, "")

    @gl.public.view
    def get_verdict(self, proof_id: str) -> str:
        return self.verdicts.get(proof_id, "")

    @gl.public.view
    def get_total(self) -> u256:
        return self.total_submissions

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner
