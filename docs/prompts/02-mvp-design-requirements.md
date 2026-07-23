
# Problem Statement  

Consider the following business requirements:  
Each GEICO system has a status (IN-DEVELOPMENT, IN-PRODUCTION)  
Each GEICO system must have a system design doc  
Each system design doc should be evaluated via LLM bot  
Each GEICO system can transition from development to production iff the system design doc has been approved

## MVP Requirements

implement only
- Create a system with a design document
- Retrieve the system
- Evaluate the document
- Transition the system to production
- Block transition unless the document is approved
- Use in memory storage 
- Add a few API tests

## Data Model
System
- id
- name
- status: IN-DEVELOPMENT | IN-PRODUCTION
- design_doc

DesignDoc
- content
- evaluation_status: NOT-EVALUATED | APPROVED | REJECTED
- evaluation_feedback: string | null

## constraints
system may transition to IN-PRODUCTION only when evaluation_status == APPROVED.

## API Design (minimal)
POST /systems
GET /systems/{system_id}
POST /systems/{system_id}/design-doc/evaluate
PUT /systems/{system_id}/design-doc
POST /systems/{system_id}/promote

