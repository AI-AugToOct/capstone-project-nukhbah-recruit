
# Defines role-based evaluation rubrics and groupings
# for LLM-as-a-Judge scoring.

EVALUATION_CRITERIA = {
    "ai_engineer": {
        "Python Proficiency": {
            "weight": 0.20,
            "group": "Quality",
            "description": "Correct use of Python syntax, data structures, and ML libraries such as NumPy, pandas, TensorFlow, or PyTorch."
        },
        "ML/DL Knowledge": {
            "weight": 0.30,
            "group": "Logic",
            "description": "Understanding of model architectures, training procedures, loss functions, and evaluation metrics."
        },
        "Data Handling & Preprocessing": {
            "weight": 0.20,
            "group": "Logic",
            "description": "Proper data cleaning, normalization, feature engineering, and validation splitting."
        },
        "Problem Solving & Reasoning": {
            "weight": 0.20,
            "group": "Logic",
            "description": "Ability to diagnose issues, interpret results, and adapt the pipeline logically."
        },
        "Optimization & Efficiency": {
            "weight": 0.10,
            "group": "Performance",
            "description": "Efficiency of model training and inference; avoidance of redundant computations."
        },
    },

    "cyber_security": {
        "Security Concepts": {
            "weight": 0.30,
            "group": "Security",
            "description": "Understanding of vulnerabilities, encryption, authentication, and access control principles."
        },
        "Log Analysis & Threat Detection": {
            "weight": 0.25,
            "group": "Logic",
            "description": "Ability to detect anomalies or malicious activity from log data or code patterns."
        },
        "Code Logic & Response Handling": {
            "weight": 0.20,
            "group": "Logic",
            "description": "Accuracy and correctness in implementing detection and response logic."
        },
        "Tool & Framework Knowledge": {
            "weight": 0.15,
            "group": "Quality",
            "description": "Proficiency with security tools (SIEMs, IDS/IPS, scripting) for automation or analysis."
        },
        "Best Practices": {
            "weight": 0.10,
            "group": "Quality",
            "description": "Adherence to secure coding standards and compliance guidelines."
        },
    },

    "software_engineer": {
        "Algorithm Design": {
            "weight": 0.30,
            "group": "Logic",
            "description": "Design of algorithms with correct logic, scalability, and optimal complexity."
        },
        "Code Logic & Structure": {
            "weight": 0.25,
            "group": "Logic",
            "description": "Program flow, modularity, and proper error handling."
        },
        "Data Structures Usage": {
            "weight": 0.20,
            "group": "Logic",
            "description": "Appropriate selection and manipulation of arrays, trees, hash maps, etc."
        },
        "Optimization & Efficiency": {
            "weight": 0.15,
            "group": "Performance",
            "description": "Resource management, computational efficiency, and time/space trade-offs."
        },
        "Code Quality & Readability": {
            "weight": 0.10,
            "group": "Quality",
            "description": "Naming conventions, documentation, and maintainable style."
        },
    },

    "cloud_engineer": {
        "Cloud Architecture Concepts": {
            "weight": 0.30,
            "group": "Logic",
            "description": "Knowledge of distributed systems, scaling, and cloud service models (AWS, Azure, GCP)."
        },
        "Infrastructure as Code": {
            "weight": 0.25,
            "group": "Quality",
            "description": "Implementation of infrastructure automation using Terraform, CloudFormation, etc."
        },
        "Automation & CI/CD": {
            "weight": 0.20,
            "group": "Performance",
            "description": "Continuous integration and deployment pipelines, automation reliability."
        },
        "Security & Compliance": {
            "weight": 0.15,
            "group": "Security",
            "description": "IAM roles, encryption, secure configuration, and compliance awareness."
        },
        "Best Practices": {
            "weight": 0.10,
            "group": "Quality",
            "description": "Resource optimization, version control, monitoring, and cost efficiency."
        },
    },

    "full_stack_developer": {
        "Frontend/Backend Integration": {
            "weight": 0.30,
            "group": "Logic",
            "description": "Data flow and logical consistency between frontend and backend components."
        },
        "API Design & Implementation": {
            "weight": 0.25,
            "group": "Logic",
            "description": "RESTful architecture, endpoint consistency, and proper error/status handling."
        },
        "Code Structure & Modularity": {
            "weight": 0.20,
            "group": "Quality",
            "description": "Component reusability, project organization, and separation of concerns."
        },
        "Database & Query Efficiency": {
            "weight": 0.15,
            "group": "Performance",
            "description": "Schema design, query optimization, and transaction management."
        },
        "Best Practices": {
            "weight": 0.10,
            "group": "Quality",
            "description": "Security validation, maintainable code standards, and testing discipline."
        },
    },
}

# Criteria groups for analytics / visualization
CRITERIA_GROUPS = {
    "Logic": [
        "Problem Solving & Reasoning",
        "Algorithm Design",
        "Code Logic & Structure",
        "Frontend/Backend Integration",
        "ML/DL Knowledge",
        "Data Handling & Preprocessing",
        "Cloud Architecture Concepts",
        "API Design & Implementation",
        "Log Analysis & Threat Detection",
    ],
    "Performance": [
        "Optimization & Efficiency",
        "Automation & CI/CD",
        "Database & Query Efficiency",
    ],
    "Quality": [
        "Code Quality & Readability",
        "Code Structure & Modularity",
        "Infrastructure as Code",
        "Tool & Framework Knowledge",
        "Best Practices",
        "Python Proficiency",
    ],
    "Security": [
        "Security & Compliance",
        "Security Concepts",
    ],
}

class EvaluationCriteria:
    """Utility wrapper to fetch criteria and weights for a specific role."""

    def __init__(self, role: str):
        key = role.lower().replace(" ", "_")
        if key not in EVALUATION_CRITERIA:
            raise ValueError(f"Unknown role '{role}'. Must be one of: {list(EVALUATION_CRITERIA.keys())}")
        self.criteria = EVALUATION_CRITERIA[key]

    def get_weights(self):
        """Return {criterion: weight}"""
        return {k: v["weight"] for k, v in self.criteria.items()}

    def get_descriptions(self):
        """Return {criterion: description}"""
        return {k: v["description"] for k, v in self.criteria.items()}

    def get_groups(self):
        """Return {criterion: group}"""
        return {k: v["group"] for k, v in self.criteria.items()}
