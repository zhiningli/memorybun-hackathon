from pydantic import BaseModel
from typing import Dict, Any

class Context(BaseModel):
    """
    Container for context (rubric, reference answer, question).
    """
    def to_prompt(self) -> str:
        raise NotImplementedError("Context must implement to_prompt method")

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Context must implement to_dict method")


class QuestionContext(Context):
    """
    Container for question context (rubric, reference answer, question).
    """
    rubric: Dict[str, Any]
    reference_answer: Dict[str, Any]
    question: Dict[str, Any]
    question_id: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rubric": self.rubric,
            "reference_answer": self.reference_answer,
            "question": self.question,
            "question_id": self.question_id
        }

    def to_prompt(self) -> str:
        """
        Format context as a structured prompt section for the LLM.
        
        Returns formatted string with question, reference answer, and rubric.
        """
        parts = []
        
        # Question section
        if self.question:
            question_title = self.question.get("title", "")
            question_details = self.question.get("question_details", "")
            parts.append(f"QUESTION: {question_title}")
            if question_details:
                parts.append(f"{question_details}")
        
        # Reference answer section
        if self.reference_answer:
            parts.append("\nREFERENCE ANSWER:")
            text_answer = self.reference_answer.get("text_answer")
            if text_answer:
                parts.append(f'"""\n{text_answer}\n"""')
            
            # Include ideal structure if available
            ideal_structure = self.reference_answer.get("ideal_answer_structure")
            if ideal_structure:
                parts.append("\nIdeal Answer Structure:")
                for i, step in enumerate(ideal_structure, 1):
                    parts.append(f"  {i}. {step}")
            
            # Include key constraints if available
            key_constraints = self.reference_answer.get("key_constraints_to_mention")
            if key_constraints:
                parts.append("\nKey Points to Address:")
                for constraint in key_constraints:
                    parts.append(f"  - {constraint}")
        
        # Rubric section (formatted for grading)
        # Only 'dimensions' format is supported
        if self.rubric and 'dimensions' in self.rubric:
            dimensions = self.rubric['dimensions']
            
            parts.append("\n" + "="*50)
            parts.append("GRADING RUBRIC (Total: 10 marks)")
            parts.append("="*50)
            parts.append("You MUST score the student on EACH of the following dimensions:")
            
            for dim in dimensions:
                name = dim['name']
                max_marks = dim['weight'] * 10
                description = dim['description']
                
                parts.append(f"  • {name} ({max_marks:.1f} marks): {description}")
                
                criterias = dim.get('criterias', [])
                if criterias:
                    parts.append("    Criteria:")
                    for crit in criterias:
                        c_name = crit.get('name', 'Criteria')
                        c_cond = crit.get('scoring_condition', '')
                        parts.append(f"    - {c_name}: {c_cond}")
            
            # Explicit list of dimension names
            dimension_names = [dim['name'] for dim in dimensions]
            parts.append(f"\nIMPORTANT: Your score_breakdown MUST include ALL of: {dimension_names}")
        
        return "\n".join(parts)
