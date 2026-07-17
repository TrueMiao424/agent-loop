class TaskStep:
    REQUIREMENT_REFINEMENT = "Requirement_Refinement"
    HUMAN_REVIEW_1 = "Human_Review_1"
    AUTO_DEVELOPMENT = "Auto_Development"
    HUMAN_REVIEW_2 = "Human_Review_2"
    COMMIT_PUSH = "Commit_Push"


class TaskStatus:
    INIT = "Init"
    PROCESSING = "Processing"
    FINISHED = "Finished"
    FAILED = "Failed"
    INTERRUPTED = "Interrupted"
    CANCELLED = "Cancelled"


class SessionStatus:
    PROCESSING = "Processing"
    FINISHED = "Finished"
    FAILED = "Failed"
    INTERRUPTED = "Interrupted"
