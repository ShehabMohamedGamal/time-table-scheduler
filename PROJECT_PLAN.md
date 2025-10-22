# Automated Timetable Generation CSP Project Plan

## Project Overview

Build a constraint-based timetable scheduler using the existing SQLite database that:

1. Satisfies all hard/soft constraints from requirements
2. Integrates level-based course structure from levels.json
3. Uses existing database schema without modifications

## Core Components

### 1. Data Layer (Days 1-2)

- Database Interface (using existing schema)
- Level Parser (for levels.json)
- Data Validation
- Conflict Detection

### 2. CSP Engine (Days 3-5)

- Variable Definition
  - Each course-level combination as variable
  - Domain: (timeslot × room × instructor) from DB
- Constraint Implementation
  - Hard Constraints (from requirements)
    - No instructor/room double booking
    - Course-room type matching
    - Level requirements (from levels.json)
  - Soft Constraints
    - Student gap minimization
    - Time preference handling
- Solver Implementation
  - Backtracking with forward checking
  - AC-3 constraint propagation
  - Solution validation

### 3. Core Services (Days 6-8)

- Timetable Generator
  - Level-based scheduling
  - Constraint satisfaction
  - Solution optimization
- Data Management
  - CRUD operations
  - Bulk updates
  - Validation rules
- Solution Validator
  - Constraint checking
  - Conflict detection
  - Quality metrics

### 4. Interface & Testing (Days 9-10)

- REST API
  - CRUD endpoints
  - Generation endpoints
  - Validation endpoints
- Testing Suite
  - Unit tests
  - Integration tests
  - Performance tests
- Documentation
  - API documentation
  - User guide
  - Technical specs

## Implementation Details

### Database Integration

Uses existing schema from timetable.db:

- courses: Course definitions and types
- timetable: Time slot assignments
- rooms: Available spaces
- instructors: Faculty data
- qualified_courses: Teaching qualifications

### Level Integration

- Parse levels.json structure
- Map to courses table
- Validate course existence
- Handle course groups/options

### Constraint Implementation

Hard Constraints:

1. No resource conflicts
2. Room type matching
3. Level requirements
4. Course prerequisites

Soft Constraints:

1. Gap minimization
2. Instructor preferences
3. Room utilization
4. Level distribution

### Testing Strategy

1. Unit Tests

   - Schema validation
   - Constraint checking
   - Level parsing
   - Solution validation

2. Integration Tests

   - End-to-end scheduling
   - Data consistency
   - API functionality

3. Performance Tests
   - Generation time
   - Resource usage
   - Concurrent access

## Success Criteria

1. All hard constraints satisfied
2. Soft constraints optimized
3. Performance targets met
4. Data integrity maintained
5. User requirements fulfilled

## Risk Mitigation

1. Database bottlenecks: Implement caching
2. Performance issues: Optimize solver
3. Data consistency: Validate inputs
4. Integration problems: Comprehensive testing

## Timeline

- Days 1-2: Data Layer
- Days 3-5: CSP Engine
- Days 6-8: Core Services
- Days 9-10: Interface & Testing
