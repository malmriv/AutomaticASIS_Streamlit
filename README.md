# 🔍 SAP Integration Suite explorer

- This repo backs a web app you can find [here](https://integration-report.streamlit.app/).
- The app is meant to help out in SAP Integration Suite development: you upload an integration package, and it gives you back a full `.csv` report listing all the endpoints (calls) found across your tenant. It’s a quick way to get a clear picture of what’s currently running.
- The original scripts were first shared [here](https://github.com/malmriv/AutomaticASIS), and I’ve decided to keep the repo as-is since this link was already being passed around internally before the app was wrapped up and published.
- You’ll find the technical details below in this README.

---

## Context

To govern a company's integration landscape effectively, it's essential to have a clear understanding of:

1. Which systems are connected to which
2. What calls are being made, internally and externally
3. What technologies and protocols are used
4. What the internal integration structure looks like

Answering these questions isn’t trivial and usually requires a team of skilled consultants. The challenge is that the low-level work involved is time-consuming, tiresome, prone to mistakes, and quickly becomes outdated as the landscape evolves. That’s why I built this app.

**So, what does this app do?**  
It automates the low-level discovery work in an SAP Integration Suite tenant. You upload one or more integration flow packages (`.zip` files), and it returns a detailed `.csv` report that you can open in Excel, Google Sheets, or similar tools.

---

## How does it work?
### General overview

When you upload files to the app via drag-and-drop, here's what happens under the hood:

- Files are saved temporarily and automatically cleaned up after processing.
- A Python script unzips all the `.zip` files.
- Inside, it finds extensionless files like `{iflow}_content`; these are the actual integration flows.
- Those are repackaged as `.zip` and unzipped again.
- The script then parses the `.iflw` file in each folder and extracts metadata from every message flow:
  - Component type (e.g. SOAP, HTTPS, JMS, SFTP, JDBC...)
  - Direction (Sender or Receiver)
  - Adapter name
  - Transport protocol (e.g. HTTPS, SFTP, JDBC...)
  - Address/host (e.g. `https://mycrm.company.com/api/v1`)
- After that, a second script analyzes the `.csv` and adds two extra columns with internal call mappings ("who calls whom").
- Everything is packaged in a Docker container which runs on [Streamlit](https://streamlit.io/). Disclaimer: I did use Google's [gemini-cli](https://github.com/google-gemini/gemini-cli) help for this part, because I had never used Streamlit before. I knew services like Vercel or Render, but they do not seem to allow temporary file creation. So, if anything does not work well, please let me know!

### Key features

- Supports parameter substitution using `parameters.prop` (note: only default values are available).
- Flags each address as parameterized or not (`IsParametrized = true/false`)
- Extracts IFlow ID and version from the `MANIFEST.MF` file
- Handles direction-aware address keys (e.g. separate keys for JMS inbound vs outbound)

---

### Parameter substitution

- Parameters are detected using `{{param_name}}` syntax.
- Values are pulled from the `parameters.prop` file inside each IFlow.
- If a value is found, it replaces the placeholder and marks `IsParametrized` as true.
- If not, the placeholder is left in place, but it's still marked as parameterized.

---

### Supported adapter types and address keys

The app supports the most commonly used SAP CPI adapters. Each adapter exposes its connectivity info in a specific field:

| Adapter Type  | Address Field (Direction-Specific When Needed)           |
|---------------|----------------------------------------------------------|
| HTTPS         | `urlPath`                                                |
| HTTP          | `httpAddressWithoutQuery`                                |
| SFTP          | `host`                                                   |
| JMS           | `QueueName_inbound` (sender), `QueueName_outbound` (receiver) |
| ProcessDirect | `address`                                                |
| HCIOData      | `address`                                                |
| SOAP          | `address`                                                |
| JDBC          | `alias`                                                  |
| PollingSFTP   | `host`                                                   |

---


## Output

The web app generates a CSV file `processed_result.csv` with the following columns:

### Example output

Below is an example snippet of the `.csv` output you can expect after uploading a package:
| UID     | Package                                           | Iflow                          | IflowID                                       | IflowVersion | AdapterType   | TransportProtocol | AdapterDirection | AdapterName     | AdapterVersion | AdapterAddress                                                               | IsParametrized | CallsIflow | IsCalledByIflow |
|---------|---------------------------------------------------|--------------------------------|------------------------------------------------|--------------|----------------|--------------------|------------------|------------------|----------------|--------------------------------------------------------------------------------|----------------|------------|------------------|
| SCDC-3  | SAP Customer Data Cloud generic and shared integrations | CDC fetch magic link          | zcrm.scenarios...getMagicLink                  | 1.0.4        | HTTP           | HTTP               | Receiver         | HTTP             | 1.14           | https://accounts.eu1.example.com/accounts.auth.magiclink.getlink              | True           |            |                  |
| SCDC-5  | SAP Customer Data Cloud generic and shared integrations | CDC import full account batch | zcrm.scenarios...importFullAccountBatch        | 1.0.0        | HTTPS          | HTTPS              | Sender           | HTTPS            | 1.5            | /zcrm/cdcImportFull/batch                                                    | True           |            |                  |
| SCDC-6  | SAP Customer Data Cloud generic and shared integrations | CDC set account data          | zcrm.scenarios...setAccountInfoBatch           | 1.0.1        | HTTP           | HTTP               | Receiver         | HTTP             | 1.14           | https://accounts.eu1.example.com/accounts.setAccountInfo                      | True           |            |                  |
| SCDC-10 | SAP Customer Data Cloud generic and shared integrations | CDC create relation           | zcrm.scenarios...createRelation                | 1.0.3        | ProcessDirect  | Not Applicable     | Sender           | ProcessDirect    | 1.1            | /internal-dev/createRelationCDC                                               | True           |            |                  |
| SCDC-15 | SAP Customer Data Cloud generic and shared integrations | CDC set account info hub      | zcrm.scenarios...setAccountInfoHUB             | 1.0.33       | ProcessDirect  | Not Applicable     | Sender           | ProcessDirect    | 1.1            | /internal-dev/setAccountInfoHUB                                               | True           | SCDC-14    |                  |

---

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**.

You are free to:

- Share — copy and redistribute the material in any medium or format  
- Adapt — remix, transform, and build upon the material

Under the following terms:

- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.  
- **NonCommercial** — You may not use the material for commercial purposes.

For more details, see the full license text [here](https://creativecommons.org/licenses/by-nc/4.0/).

