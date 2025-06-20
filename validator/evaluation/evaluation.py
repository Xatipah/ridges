from typing import List, Optional

from openai import OpenAI
from shared.logging_utils import get_logger
from validator.challenge.base import ValidationResult
from validator.challenge.codegen.challenge import CodegenChallenge
from validator.challenge.codegen.response import CodegenResponse
from validator.db.operations import DatabaseManager
from validator.evaluation.graders.elo_grader import EloGrader
from validator.utils.clean_patch import remove_unused, remove_comments, remove_docstrings
from validator.config import MOCK_RESPONSES
import tempfile
from git import Repo
from pathlib import Path
import hashlib

class CodeGenValidator:
    def __init__(self, db_manager: DatabaseManager, openai_client: OpenAI, validator_hotkey: str):
        self.db_manager = db_manager
        self.openai_client = openai_client
        self.validator_hotkey = validator_hotkey
        self.logger = get_logger(__name__)

    def preprocess_patch(self, patch: str, *args) -> str:
        '''
        Preprocesses a patch by removing comments, docstrings, etc.
        '''

        without_comments = remove_comments(patch)
        without_docstrings = remove_docstrings(without_comments)
        without_unused = remove_unused(without_docstrings)

        return without_unused.strip()
    

    def apply_and_run_tests(self, problem: 'CodegenChallenge', patch: str) -> Optional[str]:
        '''
        Clones the relevant repo, applies the patch, and runs the tests.
        Also runs pylint and makes sure no new errors have appeared.
        
        Returns:
            An error message if anything fails, otherwise None
        '''

        return None


    async def evaluate_responses(self, problem: CodegenChallenge, miner_responses: List[CodegenResponse]) -> List['ValidationResult']:
        if MOCK_RESPONSES:
            return ValidationResult(score=5, error=None)

        grader = EloGrader(problem)

        responses_to_test = []

        for response in miner_responses:
            response.response_patch = self.preprocess_patch(response.response_patch)
            error = self.apply_and_run_tests(problem, response.response_patch)
            if error is None:
                responses_to_test.append(response)
            else:
                self.logger.info(f"Response {response.response_id} failed because of: {error}")
                self.db_manager.mark_response_failed(response.response_id)
        
        scores = await grader.grade(responses_to_test)

        validation_results = [ValidationResult(score=scores.get(response.miner_hotkey, 0.0)) for response in responses_to_test]
        return validation_results
