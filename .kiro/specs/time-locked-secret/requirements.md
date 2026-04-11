# Requirements Document

## Introduction

A web-based application that allows users to store a secret (password or text note) and restrict access to it within a specific time window. Outside of the defined time period, the content is inaccessible. The application is built in Python and served via a web interface.

## Glossary

- **Secret**: A user-provided piece of text, such as a password or note, intended to be kept confidential.
- **Time_Window**: A user-defined period defined by a start datetime and an end datetime during which the Secret is accessible.
- **Creator**: A user who creates and configures a Secret along with its Time_Window.
- **Viewer**: A user who attempts to access a Secret via its unique link.
- **Secret_Store**: The server-side component responsible for persisting and retrieving Secrets.
- **Access_Controller**: The server-side component responsible for evaluating whether the current time falls within the Time_Window.
- **Secret_Link**: A unique URL generated for each Secret that Viewers use to access it.

---

## Requirements

### Requirement 1: Create a Secret

**User Story:** As a Creator, I want to input a secret and define a time window, so that I can share it with others who can only view it during that period.

#### Acceptance Criteria

1. THE Secret_Store SHALL accept a Secret of up to 10,000 characters.
2. WHEN a Creator submits a Secret with a valid Time_Window, THE Secret_Store SHALL persist the Secret and return a unique Secret_Link.
3. THE Secret_Store SHALL require both a start datetime and an end datetime to form a valid Time_Window.
4. IF the end datetime is not after the start datetime, THEN THE Secret_Store SHALL return a descriptive validation error.
5. IF the Secret field is empty, THEN THE Secret_Store SHALL return a descriptive validation error.

---

### Requirement 2: Access a Secret Within the Time Window

**User Story:** As a Viewer, I want to open a Secret_Link during the allowed time window, so that I can read the secret content.

#### Acceptance Criteria

1. WHEN a Viewer requests a Secret_Link and the current server time is within the Time_Window, THE Access_Controller SHALL return the Secret content.
2. WHEN a Viewer requests a Secret_Link and the current server time is before the Time_Window start, THE Access_Controller SHALL return a message indicating the Secret is not yet available and the time it becomes available.
3. WHEN a Viewer requests a Secret_Link and the current server time is after the Time_Window end, THE Access_Controller SHALL return a message indicating the Secret has expired.
4. IF a Viewer requests a Secret_Link that does not exist, THEN THE Access_Controller SHALL return a 404 not found response.

---

### Requirement 3: Time Zone Handling

**User Story:** As a Creator, I want to specify the time zone for my time window, so that the access period is accurate regardless of where Viewers are located.

#### Acceptance Criteria

1. THE Secret_Store SHALL require the Creator to select a time zone when defining a Time_Window.
2. WHEN evaluating access, THE Access_Controller SHALL compare the current UTC time against the Time_Window stored in UTC.
3. THE Secret_Store SHALL convert the Creator-provided start and end datetimes from the selected time zone to UTC before persisting.

---

### Requirement 4: Secret Expiry and Cleanup

**User Story:** As a system operator, I want expired secrets to be removed, so that the storage does not grow indefinitely.

#### Acceptance Criteria

1. WHILE a Secret's Time_Window end datetime has passed by more than 24 hours, THE Secret_Store SHALL mark the Secret as eligible for deletion.
2. THE Secret_Store SHALL delete all Secrets eligible for deletion during a scheduled cleanup that runs at least once every 24 hours.

---

### Requirement 5: Secret Link Uniqueness and Security

**User Story:** As a Creator, I want my Secret_Link to be unguessable, so that only people I share it with can attempt to access the Secret.

#### Acceptance Criteria

1. THE Secret_Store SHALL generate each Secret_Link using a cryptographically random identifier of at least 128 bits of entropy.
2. THE Secret_Store SHALL NOT expose sequential or predictable identifiers in Secret_Links.

---

### Requirement 6: Web Interface

**User Story:** As a Creator or Viewer, I want a simple web interface, so that I can create and access secrets without using an API directly.

#### Acceptance Criteria

1. THE Web_Interface SHALL provide a form for Creators to input a Secret, a start datetime, an end datetime, and a time zone.
2. WHEN a Secret is successfully created, THE Web_Interface SHALL display the Secret_Link to the Creator.
3. THE Web_Interface SHALL provide a page at the Secret_Link URL that displays the Secret content or an appropriate access-denied message based on the current time.
4. WHEN a Creator submits the creation form with invalid input, THE Web_Interface SHALL display the validation error returned by the Secret_Store without reloading the page state.
