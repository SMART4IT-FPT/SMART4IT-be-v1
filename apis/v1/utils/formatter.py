import pandas as pd
from datetime import datetime

def format_education(education):
    return "\n\n".join([
        "\n".join(filter(None, [
            " - ".join(filter(None, [e.get("Degree", ""), e.get("Major", "")])),
            e.get("Institution", ""),
            f"Graduation Year: {e['GraduationYear']}" if e.get("GraduationYear") else ""
        ]))
        for e in education
    ])

def format_work_experience(work):
    return "\n\n".join([
        "\n".join(filter(None, [
            f"{w.get('JobTitle', '')} at {w.get('CompanyName', '')}".strip(),
            "From {} to {}".format(w.get("Duration", {}).get("StartDate", ""), w.get("Duration", {}).get("EndDate", "")).strip("From to "),
            w.get("KeyResponsibilitiesAndAchievements", "")
        ]))
        for w in work
    ])

def format_certifications(certs):
    return "\n".join([
        " - ".join(filter(None, [
            c.get("CertificationName", ""),
            c.get("IssuingOrganization", "")
        ])) + (f" ({c['DateObtained']})" if c.get("DateObtained") else "")
        for c in certs
    ])

def format_languages(langs):
    return "\n".join([
        " - ".join(filter(None, [
            l.get("Language", ""),
            l.get("ProficiencyLevel", "")
        ]))
        for l in langs
    ])

def build_cv_summary_file(cvs):
    # Sort by upload_at (newest first)
    cvs = sorted(cvs, key=lambda x: datetime.fromisoformat(x["upload_at"]), reverse=True)

    rows = []
    for i, cv in enumerate(cvs, start=1):
        summary = cv["summary"]
        pi = summary.get("PersonalInformation", {})
        contact = pi.get("ContactInformation", {})
        skills = summary.get("Skills", {})
        row = {
            "ID": i,  # Sequential ID
            "upload_at": cv["upload_at"],
            "Name": pi.get("FullName", ""),
            "Email": contact.get("Email", ""),
            "Phone Number": contact.get("PhoneNumber", ""),
            "Address": contact.get("Address", ""),
            "Professional Summary": summary.get("ProfessionalSummary", ""),
            "Education": format_education(summary.get("Education", [])),
            "Technical Skills": ", ".join(skills.get("TechnicalSkills", [])),
            "Work Experience": format_work_experience(summary.get("WorkExperience", [])),
            "Soft Skills": ", ".join(skills.get("SoftSkills", [])),
            "Certifications": format_certifications(summary.get("CertificationsAndTraining", [])),
            "Languages": format_languages(summary.get("Languages", []))
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.drop(columns=["upload_at"], inplace=True)
    return df