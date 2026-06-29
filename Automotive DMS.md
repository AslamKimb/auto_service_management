automotive dealerships and repair garages.

Below is an overview of the modules and features visible and demonstrated in this program.

---

### I. Core ERP & Financial Modules (Main Navigation Sidebar)
The main navigation pane on the left contains 10 primary modules that manage both the general business operations and specific workshop functions:

1. **Ledger (G/L):** Manages core financial accounting, general ledger entries, chart of accounts, and financial reporting.
2. **Customer:** Manages accounts receivable, customer profiles, billing addresses, contact details, and payment/credit terms (as seen with the corporate account for *MTN Uganda Limited*).
3. **Vendor:** Handles accounts payable and relationships with parts suppliers and external service vendors.
4. **Inventory:** Manages warehouse stock, including spare parts (e.g., batteries, fluids, filters), pricing, cost margins, quantities, and bin storage locations.
5. **Sales:** Processes general sales orders, retail parts sales, and direct customer invoicing.
6. **Purchase:** Manages purchase orders, stock replenishment, and the receiving of parts from suppliers.
7. **Project (Jobs):** Tracks larger resource-planning projects, scheduling, and specialized multi-step service tasks.
8. **DMS (Dealer Management System):** The core module dedicated to vehicle service management, vehicle registry, and workshop tasks.
9. **Assets:** Tracks the garage’s physical assets, such as vehicle lifts, diagnostic machinery, workshop tools, and company fleet vehicles.
10. **General:** Handles administrative system setups, user permissions, localization settings, and general system configurations.

---

### II. DMS (Dealer Management System) Module Features
The DMS module contains specialized automotive submenus and database tables:

*   **Daily Tasks Menu:**
    *   **Jobcard Overview:** A central dashboard used to monitor the status of all planned, open, or closed workshop jobs.
    *   **New Jobcard:** Initiates a service request. The system opens a template (seen in the video) where advisors enter key vehicle/customer metrics including vehicle registration, customer account, mileage, type of service, promised delivery dates, and diagnostic remarks.
    *   **Find Jobcard:** Allows users to quickly search for existing or historic service jobs by entering their unique ID number (such as Job Card `743425` [1.32]).
    *   **Find Vehicle (VIF):** A search tool using the *Vehicle Integration File* database to find a vehicle record by Registration Number, Chassis/VIN, Engine Number, or Model Code.
    *   **Find Order:** Looks up active service orders.
    *   **Open DMS Web:** Integrates the local database client with web-based portal features.
*   **Tables Submenu:**
    *   **VIF – Service:** Tracks the exhaustive chronological service history of a vehicle, recording every past job card, odometer reading, and work description.
    *   **VIF – Buy/Sell:** Logs transaction and ownership changes of vehicles (primarily for dealership trade-ins).
    *   **VIF – Availability:** Monitors the availability of fleet or service loaner vehicles.

---

### III. Job Card Execution & Action Sidebar Features
When a job card (such as `743425`) is opened, a vertical menu on the right provides tools to manage workshop workflows:

*   **Communication & Operations:**
    *   **Print:** Generates the standardized yellow hardcopy job card [1.32] (which includes a vehicle diagram for mapping exterior damage, and terms/conditions).
    *   **SMS & Email:** Enables quick, automated updates directly to the customer when a vehicle enters the shop or is ready for pickup.
    *   **Get Parts & Get Flat Rates:** Integrates labor databases to estimate standardized repair times (flat rates) and allocate correct parts directly from inventory.
    *   **Prepare Invoice:** Converts the finalized job card, labor times, and parts used into a customer invoice.
*   **Data Editing & Administrative Tools:**
    *   **State Change:** Progresses job cards through phases (e.g., *Planned, In Progress, Awaiting Parts, Finished*).
    *   **Edit Time:** Allows for tracking and manual editing of individual mechanic labor logs.
    *   **Change Reg. No. / Change Account / Change Planned Date:** Offers flexibility to correct mistakes or adjust booking details without deleting the entire job card file.
    *   **Move Jobcard to Another Vehicle:** Reassigns service lines to a different vehicle profile if logged incorrectly.
*   **Log (Audit Trail System):**
    *   **Show Log:** Accesses a highly transparent audit trail of all manual and automated actions performed on the record. As shown in the video, this lists the date, exact time, user initials, and the exact nature of the change (e.g., *"Line deleted"*, *"Changed price from 45,000 to 35,000"*, or *"Service GatePass not final"*).

the standard **Vehicle System Workflow** in this workshop environment operates through a structured six-stage cycle. 

This workflow connects physical workshop floor activities with digital ERP tracking, ensuring accountability, inventory management, and accurate billing.

---

### Stage 1: Vehicle Intake & Pre-Inspection (Reception)
*   **Physical Action:** The vehicle arrives at the workshop. The service advisor performs a visual walk-around inspection, mapping any pre-existing exterior damage (such as dents or scratches) directly onto the vehicle diagram printed at the bottom of the physical yellow Job Card.
*   **System Action:**
    *   The operator queries the system using the **Find Vehicle (VIF)** search tool. They enter the license plate (e.g., `UAW574V`) or Chassis Number to verify if the vehicle is already registered in the system.
    *   If registered, past service history and active corporate accounts (such as *MTN Uganda Limited*) are automatically pulled up. If it is a new vehicle, a new VIF record is created.
    *   The current vehicle odometer reading (e.g., `236459 km`) is physically noted and logged in the system.

### Stage 2: Job Card Creation & Planning
*   **System Action:**
    *   The operator uses the **New Jobcard** function to generate a unique digital job card number (e.g., `743425`).
    *   They input metadata: the primary symptom or request (e.g., *"Repair of vehicle - BATTERY"*), the assigned service advisor, and the scheduling parameters (such as the *Planned* start date and *Promised Delivery* date: `05.06.2026`).
    *   The digital job card is printed as a physical yellow ticket, which is signed by the customer or corporate agent to authorize the diagnostic/maintenance work under the garage’s terms and conditions.

### Stage 3: Diagnostics & Work Allocation (Workshop floor)
*   **Physical Action:** The physical yellow job card is placed on the vehicle's windshield or dashboard, and the car is assigned to a specific workshop bay. A mechanic diagnoses the vehicle.
*   **System Action:**
    *   The job card’s status is updated via **State Change** from *Planned* to *In Progress*.
    *   If additional problems are found during diagnostics, the advisor contacts the customer for further authorization before proceeding (as standard terms specify that work will not be started without consent). 

### Stage 4: Parts Requisition & Labor Tracking
*   **System Action:**
    *   The technician requests replacement parts (e.g., a maintenance-free N70 battery, engine oil, or brake fluid). 
    *   The service advisor uses the **Get Parts** feature to locate and allocate specific item numbers (e.g., item code `EX NGS N70 PALLM` or standard battery items like `EX 107`) from the digital **Inventory** module to Job Card `743425`. This automatically reserves or deducts the parts from physical stock levels.
    *   Standard labor times are added using the **Get Flat Rates** database, or specific hourly durations are logged using **Edit Time** to assign cost directly to the job.
    *   The system monitors workshop profitability by comparing "DMS Costing" (what the parts cost the garage) against the "Retail Price" billed to the customer.

### Stage 5: Quality Control, Audit & Invoicing
*   **Physical Action:** The mechanic completes the repair, tests the vehicle's electrical system/battery, and signs off on the physical job card.
*   **System Action:**
    *   The service advisor performs a quality check and reviews the digital file.
    *   Using the **Show Log** feature, the advisor or a workshop manager reviews the audit log of the job card. This step ensures that any manual adjustments—such as line deletions, price overrides, or manual discounts—are fully tracked, authorized, and free of administrative errors.
    *   The advisor changes the state to *Finished* and clicks **Prepare Invoice** to compile all approved labor lines and allocated inventory parts into a pending invoice.

### Stage 6: Gate Pass & Vehicle Release (Checkout)
*   **System Action / Physical Action:**
    *   **Payment Clearance:** The invoice is processed based on customer terms. For cash customers, payment is received at the cashier. For corporate accounts (e.g., MTN Uganda), the transaction is charged to their ledger according to agreed credit terms (e.g., "45 days").
    *   **Gate Pass Generation:** Once the financial transaction is cleared or authorized, the system generates a **Gate Pass** (noted in the log system as a "Service GatePass"). 
    *   **Release:** The security officer at the exit gate collects the printed Gate Pass, matches it with the vehicle registration, and releases the car to the customer. The job card is digitally updated to *Closed* in the DMS database, finalizing the workflow loop.



the **Purchase/Procurement and Inventory Workflow** manages how the garage forecasts, buys, receives, and stores automotive parts. This process ensures the workshop never runs out of fast-moving items (like engine oil) while tracking cost margins accurately.

---

### Phase 1: Demand Generation (Determining What to Buy)
Procurement needs are triggered in two main ways:
1.  **Min/Max Stock Levels (Automated Replenishment):** For fast-moving inventory items (e.g., spark plugs, standard filters, brake fluid), the **Inventory** module monitors stock levels. When a part's physical quantity drops below a preset safety-stock threshold, the system automatically flags it for reorder.
2.  **Job-Specific Requisitions (DMS Integration):** When a technician adds a specialized or out-of-stock part to an active Job Card (using the *"Get Parts"* tool under the **DMS** module), the system flags it as a "Backorder" or "Special Order." This directly links the pending purchase to that specific vehicle registration (e.g., `UAW574V`) and customer account [1.231].

---

### Phase 2: Purchase Order (PO) Creation
*   **System Action:**
    *   Within the **Purchase** module, the purchasing officer reviews the list of pending demands and automatically or manually groups them into a **Purchase Order (PO)**.
    *   They select a supplier from the **Vendor** module, which automatically applies the pre-negotiated payment terms, supplier address, and currency settings.
    *   The PO lists the exact spare part item numbers, quantities, and negotiated unit costs.
*   **Approval Workflow:** The system routes the PO through an internal authorization hierarchy based on total value. Once approved, the system emails or dispatches the PO to the vendor.

---

### Phase 3: Goods Receiving (Purchase Receipt / GRN)
*   **Physical Action:** The vendor delivers the parts to the warehouse along with a delivery note. 
*   **System Action:**
    *   The warehouse receiving team accesses the pending PO under the **Purchase** module.
    *   They perform a physical count and inspect the parts for damage.
    *   The clerk posts a **Purchase Receipt** (historically called a *Goods Received Note* or *GRN*) in the system, noting any discrepancies (e.g., receiving 8 batteries instead of 10).
    *   Posting the receipt immediately increases the *Quantity on Hand* in the **Inventory** database.

---

### Phase 4: Put-Away & Bin Location Management
*   **System Action:**
    *   To keep the warehouse organized and ensure parts can be retrieved instantly, the system tracks specific storage areas using Bin Codes and Locations.
    *   As shown in the video's parts inventory screen, the system logs inventory across specific zone/location identifiers [1.144, 1.157, 1.199]:
        *   `1ST FLOOR` (Bulk storage or larger assemblies).
        *   `S/CAGE` (Spare Parts Cage – typically secure cages for high-value items like batteries and specialized electronics).
        *   `S/FLOOR` (Service Floor / Fast-moving bins near workshop bays).
    *   The receiving clerk performs a "Put-Away" transaction, registering the exact storage location where the newly received parts have been placed.

---

### Phase 5: Three-Way Matching & Purchase Invoicing
*   **System Action:**
    *   When the vendor's physical invoice arrives at the accounts department, the finance team uses the **Purchase** module to perform a **Three-Way Match**:
        1.  Matches the **Purchase Order** (what was ordered).
        2.  Matches the **Purchase Receipt/GRN** (what was actually received).
        3.  Matches the **Vendor Invoice** (what is being billed).
    *   Once validated, the invoice is posted. This posts a debit to the inventory asset account, a credit to Accounts Payable under the **Vendor** ledger, and updates the core financial records in the **Ledger** (G/L) module.

---

### Phase 6: Parts Issuance to Job Cards (Consumption)
*   **System Action:**
    *   Once a job-specific part is registered as "received" in the inventory location (e.g., `S/CAGE` [1.199]), the system alerts the service advisor.
    *   The warehouse clerk issues the part directly to the specific Job Card.
    *   The inventory ledger automatically decrements the stock quantity and transfers the asset cost to the Job's *Cost of Goods Sold (COGS)* account.
    *   The exact landed purchase cost is populated into the Job Card's **DMS Costing** field [1.144, 1.199], updating the job's real-time financial margin.



In an automotive Dealership Management System (DMS) such as the Microsoft Dynamics CS platform used here, the **Sales System Workflow** covers the entire lifecycle of revenue generation: from the initial customer inquiry to billing, receipting, and managing payment terms. 

This workflow operates through the integration of the **DMS (8)**, **Sales (5)**, and **Customer (2)** modules.

---

### Phase 1: Quoting (Estimation & Authorization)
Before any physical work begins, a cost estimate must be created and authorized.
*   **System Action:** 
    *   The service advisor creates a draft job card and checks the **Quotation** flag (visible in the "Create new jobcard" window).
    *   They compile the required labor flat rates and necessary inventory parts to calculate an estimated total.
    *   The quotation document is printed or emailed to the customer for authorization.
*   **Physical Action:** The customer signs the physical authorization. As stated in the printed Terms and Conditions, *"Work will not be started without a signature."* [1.32]

---

### Phase 2: Deposits & Prepayments (Down Payments)
For large repair jobs, engine overhauls, or special-order parts that are not currently in stock, the system accommodates deposit tracking.
*   **Policy Enforcement:** Under the printed Terms and Conditions, the garage *"reserves the right to secure a 50% deposit, of the total value of the parts, prior to ordering parts..."* [1.32]
*   **System Action:**
    *   The advisor generates a **Prepayment Invoice** (or deposit request) in the **Sales** module for the required percentage (e.g., 50%).
    *   The customer pays this deposit. The cashier records this transaction in the system, posting an *Advance Receipt* that is logged as a credit against the customer's ledger.

---

### Phase 3: Sales Invoicing (Billing & Postings)
Once the workshop completes the repairs and performs quality checks, the draft job card is converted into a legal bill of sale.
*   **System Action:**
    *   The service advisor selects **Prepare Invoice** from the action sidebar on the active job card.
    *   The system imports all finalized service lines (labor hours, standard parts consumed, and shop supplies).
    *   Tax configurations are automatically calculated (such as standard Ugandan VAT, using the customer’s recorded VAT registration number, e.g., `1000028535` [1.32]).
    *   Upon posting the final **Sales Invoice**, the system:
        *   Deducts the corresponding costs from the inventory asset account.
        *   Posts the revenue to the general ledger.
        *   Charges the total outstanding balance to the **Customer Ledger** (Accounts Receivable).

---

### Phase 4: Receipting & Settlement (Payment Clearing)
The method of clearing the outstanding invoice depends on the customer’s pre-approved payment terms.

*   **Option A: Credit Accounts (Corporate Accounts)**
    *   Corporate clients (such as *MTN Uganda Limited*) operate under pre-approved credit terms (e.g., **"45days"** [1.32]). 
    *   The posted invoice remains as an open, outstanding item in the Customer Ledger. It is settled at a later date via bank transfer, matching the batch payment to multiple outstanding invoices.

*   **Option B: Cash / Cashless / Check Settlement (Immediate Pay)**
    *   Private retail customers must settle immediately before the vehicle can be released. (Terms: *"Only CASH payment will be accepted, unless satisfactory credit arrangements have been made in advance..."* [1.32]).
    *   The customer pays the remaining balance (the total invoice amount minus any initial 50% deposit).

*   **System Action (Receipting):**
    *   The cashier executes the **Prepare payment receipt** function (visible as the top action under the "Lines" menu [2.141]).
    *   They enter the payment details (Cash, Card, Mobile Money, or Check) and manually or automatically "apply" the payment to the open Sales Invoice.
    *   The system matches the receipt to the invoice, reducing the customer's outstanding debt to zero, marking the invoice as *Closed*, and granting clearance to generate a printed **Gate Pass** for vehicle release [2.21].