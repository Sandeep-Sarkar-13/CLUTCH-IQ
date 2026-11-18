from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, HRFlowable
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import HexColor
from pathlib import Path
import os, math


OUTDIR = Path(__file__).resolve().parent / "outputs"
OUTDIR.mkdir(parents=True, exist_ok=True)
navy = HexColor("#101C2C")
navy2 = HexColor("#17283D")
lime = HexColor("#D6FF5F")
muted = HexColor("#596579")
pale = HexColor("#F3F6FA")
line = HexColor("#D8E0EA")
accent = HexColor("#365D87")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitleX", parent=styles["Title"], fontName="Helvetica-Bold",
                          fontSize=29, leading=34, textColor=navy, alignment=TA_LEFT, spaceAfter=10))
styles.add(ParagraphStyle(name="CoverSubX", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=11, leading=17, textColor=muted, spaceAfter=8))
styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="Helvetica-Bold",
                          fontSize=18, leading=23, textColor=navy, spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="Helvetica-Bold",
                          fontSize=12.5, leading=16, textColor=accent, spaceBefore=9, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=9.2, leading=14, textColor=HexColor("#263244"), spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=7.8, leading=11, textColor=muted, spaceAfter=4))
styles.add(ParagraphStyle(name="FormulaX", parent=styles["BodyText"], fontName="Courier",
                          fontSize=8.5, leading=13, textColor=navy, backColor=pale,
                          borderColor=line, borderWidth=.6, borderPadding=8,
                          spaceBefore=4, spaceAfter=8))
styles.add(ParagraphStyle(name="CalloutX", parent=styles["BodyText"], fontName="Helvetica-Bold",
                          fontSize=9, leading=14, textColor=navy, backColor=HexColor("#EEF5D9"),
                          borderColor=HexColor("#C5D98B"), borderWidth=.6, borderPadding=8,
                          spaceBefore=5, spaceAfter=9))
styles.add(ParagraphStyle(name="TableHeadX", parent=styles["BodyText"], fontName="Helvetica-Bold",
                          fontSize=7.5, leading=9, textColor=colors.white))
styles.add(ParagraphStyle(name="TableCellX", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=7.4, leading=10, textColor=HexColor("#263244")))
styles.add(ParagraphStyle(name="BulletX", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=9, leading=13, leftIndent=12, firstLineIndent=-7,
                          bulletIndent=0, textColor=HexColor("#263244"), spaceAfter=3))

def P(txt, style="BodyX"):
    return Paragraph(txt, styles[style])

def bullets(items):
    return [Paragraph("• " + x, styles["BulletX"]) for x in items]

def make_table(rows, widths=None):
    data=[]
    for ri,row in enumerate(rows):
        data.append([P(str(c), "TableHeadX" if ri==0 else "TableCellX") for c in row])
    t=Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),navy2),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.35,line),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,pale]),
    ]))
    return t

def page_decor(canvas, doc):
    canvas.saveState()
    w,h=A4
    if doc.page > 1:
        canvas.setStrokeColor(line); canvas.setLineWidth(.5)
        canvas.line(18*mm,h-15*mm,w-18*mm,h-15*mm)
        canvas.setFont("Helvetica-Bold",8); canvas.setFillColor(navy)
        canvas.drawString(18*mm,h-11.5*mm,"CLUTCH IQ")
        canvas.setFont("Helvetica",7.5); canvas.setFillColor(muted)
        canvas.drawRightString(w-18*mm,h-11.5*mm,doc.title)
    canvas.setStrokeColor(line); canvas.line(18*mm,14*mm,w-18*mm,14*mm)
    canvas.setFont("Helvetica",7); canvas.setFillColor(muted)
    canvas.drawString(18*mm,9*mm,"Research methodology document · Competition data 2022–2026")
    canvas.drawRightString(w-18*mm,9*mm,f"Page {doc.page}")
    canvas.restoreState()

def cover(title, subtitle, version_tag):
    return [
        Spacer(1,22*mm),
        P("CLUTCH IQ", "CoverSubX"),
        HRFlowable(width="100%", thickness=2, color=lime, spaceBefore=4, spaceAfter=16),
        P(title, "CoverTitleX"),
        P(subtitle, "CoverSubX"),
        Spacer(1,5*mm),
        Table([[P(version_tag, "TableHeadX")]], colWidths=[70*mm],
              style=TableStyle([("BACKGROUND",(0,0),(-1,-1),navy2),
                                ("BOX",(0,0),(-1,-1),.5,navy2),
                                ("LEFTPADDING",(0,0),(-1,-1),10),
                                ("RIGHTPADDING",(0,0),(-1,-1),10),
                                ("TOPPADDING",(0,0),(-1,-1),8),
                                ("BOTTOMPADDING",(0,0),(-1,-1),8)])),
        Spacer(1,12*mm),
        P("<b>Purpose</b><br/>A detailed explanation of the approach, data transformations, mathematical definitions, model logic, ranking procedure, assumptions and limitations. The document describes the implementation in the corresponding project code—not an idealized alternative.", "BodyX"),
        Spacer(1,8*mm),
        P("<b>How to read this document</b><br/>Start with the project overview, then follow the phases in order. Each formula is followed by a plain-language interpretation and an explanation of the variables.", "BodyX"),
        PageBreak()
    ]

def add_common_sections(story, upgraded=False):
    story += [
        P("1. Project overview", "H1X"),
        P("CLUTCH IQ is a cricket analytics framework designed to identify batters and bowlers whose performance is stronger in high-pressure situations than in normal situations. It does not directly measure a player's psychology. It operationalizes pressure through observable match-state difficulty and then compares actual performance with modelled expected performance.", "BodyX"),
        P("The project processes ball-by-ball records and match/competition metadata for T20 and T20I matches from 2022–2026. It builds pre-delivery states, assigns pressure, estimates expected performance, aggregates player-level pressure and normal samples, and produces separate batter and bowler leaderboards.", "BodyX"),
        P("2. Data inputs and preparation", "H1X"),
        make_table([
            ["Input", "Purpose"],
            ["ball_by_ball.csv", "Delivery-level runs, extras, wickets, striker, bowler, innings and delivery sequence."],
            ["matches.csv", "Match date, competition ID, innings limits, revised target, winner and match result."],
            ["competitions.csv", "Competition format and season."],
            ["teams.csv / playing_eleven.csv / competition_team_player_mapping.csv", "Supporting team and player metadata; the current core engine primarily uses ball-by-ball, match and competition tables."],
        ], [43*mm, 130*mm]),
        Spacer(1,5),
        P("2.1 Delivery accounting", "H2X"),
        P("The implementation retains innings 1 and 2 and excludes innings 3+ (extra innings/Super Overs). A delivery key is (match_id, innings, innings_ball_num); duplicate keys trigger an error. The innings limit is taken from the relevant revised-overs field, with 120 as a fallback.", "BodyX"),
        P("<b>Legal delivery:</b> a delivery is treated as legal unless extras_type is 'wide' or 'overstep'. The code interprets 'Overstep' as a no-ball; the source data dictionary should be checked to confirm this interpretation.", "BodyX"),
        P("Team runs = batter runs + extras1_runs + extras_2_runs. Bowler-conceded runs = batter runs plus wide/no-ball extras. Batter balls faced exclude wides and include no-balls. Bowler exposure uses legal balls only. Bowler-credited wickets are Caught, Bowled, LBW, Stump and Hit Wicket; run-outs are not credited to the bowler.", "BodyX"),
        P("2.2 Pre-delivery match state", "H2X"),
        P("For each delivery, the engine constructs the state immediately before that delivery: score, wickets lost/remaining, legal balls already bowled, balls remaining, innings limit, phase, target, runs required, required run rate and current run rate. The current delivery's outcome is excluded from these state fields.", "BodyX"),
        P("Chase formulas", "H2X"),
        P("RunsRequired = max(Target − ScoreBefore, 0)<br/>RRR = 6 × RunsRequired / BallsRemaining<br/>CRR = 6 × ScoreBefore / LegalBallsBefore", "FormulaX"),
        P("RRR is undefined when no balls remain and CRR is undefined before the first legal ball; the implementation handles these cases with missing values and downstream safe defaults.", "SmallX"),
        P("2.3 Situational features", "H2X"),
        P("WicketsLast12 counts wickets in the preceding 12 legal-ball window, excluding the current delivery. Collapse stress, recovery requirement, partnership dependency and a death-phase indicator are then derived from the pre-delivery state.", "BodyX"),
        P("3. Chronological modelling design", "H1X"),
        P("The data is evaluated using expanding chronological folds. In the earliest season, the first 25% of distinct match dates are used as a warm-up period and later dates are scored. For each subsequent season, training uses only earlier seasons and the current season is the scored fold. Training and scored match IDs must not overlap.", "BodyX"),
        P("This design reduces future-information leakage. It does not guarantee that every feature or label is free of all possible leakage; feature definitions and joins still require audit.", "CalloutX"),
    ]
    if not upgraded:
        story += [
            P("4. Expected-performance and win-probability models", "H1X"),
            P("The first version trains three delivery-level models on pre-delivery state features:", "BodyX"),
            *bullets([
                "<b>Expected batter runs:</b> HistGradientBoostingRegressor predicts batter runs on the delivery, clipped to 0–6.",
                "<b>Expected bowler runs conceded:</b> HistGradientBoostingRegressor predicts bowler-conceded runs, clipped to 0–10.",
                "<b>Credited wicket probability:</b> HistGradientBoostingClassifier estimates the probability of a bowler-credited wicket."
            ]),
            P("The win-probability model is a standardized LogisticRegression model with C=0.5, max_iter=500 and class_weight='balanced'. Its target is whether the batting team wins the match. Ties, no-results and abandoned matches are excluded from winner-label training.", "BodyX"),
            P("The model feature set includes innings, score, wickets before/remaining, legal balls before, balls remaining, innings limit, runs required, RRR, CRR and format code. The first-version model does not include player identifiers or the current delivery outcome.", "BodyX"),
            P("5. First-version pressure model", "H1X"),
            P("The first version combines five dimensions. MSD, WPL, RSI, SSI and PEP are designed as normalized values between 0 and 1. The weights are fixed starting assumptions, not weights learned through a formal optimization procedure.", "BodyX"),
            P("5.1 Match-State Difficulty (MSD)", "H2X"),
            P("For a chase, the implementation defines:", "BodyX"),
            P("RRRStress = clip((RRR − CRR) / 8, 0, 1)<br/>WicketStress = clip((10 − WicketsRemaining) / 10, 0, 1)<super>1.5</super><br/>MSD<sub>chase</sub> = 0.60 × RRRStress + 0.40 × WicketStress", "FormulaX"),
            P("For the first innings:", "BodyX"),
            P("FirstParStress = clip(ParScoreDeficit / 18, 0, 1)<br/>MSD<sub>first</sub> = 0.65 × FirstParStress + 0.35 × WicketStress", "FormulaX"),
            P("The RRR-versus-CRR gap represents how far the required scoring pace exceeds the current pace. Wicket stress rises non-linearly as wickets are lost. In the first version, ParScoreDeficit is only a phase/season proxy (described below), not a state-specific historical par model.", "BodyX"),
            P("5.2 Win-Probability Leverage (WPL) — first-version proxy", "H2X"),
            P("WPL<sub>proxy</sub> = 4 × WP × (1 − WP) × max(MSD, 0.35 × RSI)", "FormulaX"),
            P("WP is the predicted batting-team win probability before the delivery. The term 4×WP×(1−WP) is highest at WP=0.5 and lowest near 0 or 1. It therefore emphasizes uncertain match states. The urgency multiplier increases the proxy when match-state difficulty or resource scarcity is high.", "BodyX"),
            P("<b>Important:</b> this is not the expected absolute change in win probability over possible next-ball outcomes. It is a state-sensitivity proxy and must not be described as full outcome-based WPL.", "CalloutX"),
            P("5.3 Resource Scarcity Index (RSI)", "H2X"),
            P("RSI = 1 − [(BallsRemaining / InningsBallLimit) × (WicketsRemaining / 10)]", "FormulaX"),
            P("RSI is low when most balls and wickets remain. It rises as either resource is consumed. It is a compact proxy for the amount of batting resource left; it is not a full Duckworth-Lewis-style resource model.", "BodyX"),
            P("5.4 Situational Stress Index (SSI)", "H2X"),
            P("SSI = 0.35 × CollapseStress + 0.30 × RecoveryRequirement<br/>+ 0.20 × PartnershipDependency + 0.15 × CriticalOverFlag", "FormulaX"),
            P("CollapseStress = clip(WicketsLast12 / 3, 0, 1). RecoveryRequirement is RRR/18 for a chase and ParScoreDeficit/18 in the first innings, clipped to [0,1]. PartnershipDependency = clip(WicketsBefore/9,0,1). CriticalOverFlag is 1 in the death phase and 0 otherwise.", "BodyX"),
            P("5.5 Phase and Execution Pressure (PEP)", "H2X"),
            P("PEP = PhaseFraction × max(MSD, 0.5 × RSI)", "FormulaX"),
            P("PhaseFraction is legal balls already bowled divided by the innings ball limit, clipped to [0,1]. Phase progression only amplifies existing match/resource stress; death overs are not automatically assigned maximum pressure.", "BodyX"),
            P("5.6 Combined HDPI", "H2X"),
            P("HDPI = 100 × (0.25×MSD + 0.30×WPLproxy + 0.20×RSI + 0.15×SSI + 0.10×PEP)", "FormulaX"),
            P("The implementation labels score bands as Routine (0–40), Elevated (40–60), High (60–75), Severe (75–90) and Critical (90–100). The pressure flag used for the general HDPI is score ≥60. Endpoints are handled by the code's cut intervals.", "BodyX"),
            P("6. First-version par-score proxy", "H1X"),
            P("For first-innings deliveries, the code calculates the mean completed first-innings total by format and season, then multiplies that season-format mean by the current phase fraction. It compares that proxy par score with the actual score before the delivery.", "BodyX"),
            P("SeasonPar = mean(CompletedFirstInningsTotal | Format, Season)<br/>ProxyParScore = SeasonPar × PhaseFraction<br/>ParScoreDeficit = max(ProxyParScore − ScoreBefore, 0)", "FormulaX"),
            P("This proxy is easy to explain but coarse: it does not condition par on wickets lost or exact ball position beyond the broad phase fraction, and it uses the season-level average. It is not a full chronological state-conditioned par model.", "CalloutX"),
            P("7. Role-specific pressure scores", "H1X"),
            P("Batter Pressure Intelligence (BPI)", "H2X"),
            P("BPI = 100 × (0.35×HDPI/100 + 0.25×BatterUrgency + 0.20×DismissalRisk + 0.20×BatterResponsibility)", "FormulaX"),
            P("BatterUrgency is RRR/18 for a chase; in the first innings it combines phase fraction (55%) and par deficit/30 (45%). DismissalRisk combines a low-wickets indicator (60%) and partnership dependency (40%). BatterResponsibility combines partnership dependency (60%) and recent collapse stress (40%). BPI pressure is BPI ≥60.", "BodyX"),
            P("Bowler Pressure Intelligence (BoPI)", "H2X"),
            P("BoPI = 100 × (0.35×HDPI/100 + 0.25×BowlerDefenceUrgency + 0.20×WicketThreat + 0.20×BowlerResponsibility)", "FormulaX"),
            P("BowlerDefenceUrgency is RRR/18 for a chase; in the first innings it combines phase fraction (60%) and par deficit/30 (40%). WicketThreat combines wickets already lost/8 (50%) and recent wickets in the previous 12 legal balls (50%). BowlerResponsibility combines defence urgency (60%) and death-phase flag (40%). BoPI pressure is BoPI ≥60.", "BodyX"),
            P("8. Player performance and rankings", "H1X"),
            P("Expected-performance residuals", "H2X"),
            P("BatterResidual = ActualBatterRuns − ExpectedBatterRuns<br/>BowlerResidual = ExpectedBowlerRunsConceded − ActualBowlerRunsConceded", "FormulaX"),
            P("Positive residuals are favorable for both roles. Batter residual rewards scoring above expectation. Bowler residual rewards conceding fewer runs than expected. Credited wicket probability is retained as a separate supporting signal and is not converted into run value.", "BodyX"),
            P("Intensity weighting and exposure", "H2X"),
            P("WeightedBatterResidual = BatterResidual × (BPI/100)<super>1.5</super><br/>WeightedBowlerResidual = BowlerResidual × (BoPI/100)<super>1.5</super>", "FormulaX"),
            P("The exposure denominator is batter balls faced for batters and legal balls bowled for bowlers. Rates are calculated per 100 exposure balls, separately for pressure and normal deliveries. Pressure lift = pressure residual rate − normal residual rate.", "BodyX"),
            P("PressureRate = 100 × Σ(WeightedResidual<sub>pressure</sub>) / PressureExposure<br/>NormalRate = 100 × Σ(WeightedResidual<sub>normal</sub>) / NormalExposure<br/>RawLift = PressureRate − NormalRate", "FormulaX"),
            P("Empirical-Bayes shrinkage", "H2X"),
            P("The code uses a normal-normal shrinkage form with a zero prior mean. It estimates between-player variance τ² from the relaxed-eligible population after subtracting the average estimated sampling variance, floored at 10⁻⁸.", "BodyX"),
            P("EBLift = RawLift × τ² / (τ² + SE²)", "FormulaX"),
            P("This pulls noisier player estimates more strongly towards zero. In this implementation SE² is a variance proxy based on player-match residual variation and exposure, not a fully derived hierarchical likelihood. Interpret it as an empirical shrinkage approximation.", "BodyX"),
            P("Match-cluster bootstrap", "H2X"),
            P("For each relaxed-eligible player, the code resamples that player's match-state clusters with replacement separately for pressure and normal states. It recalculates the pressure-minus-normal rate difference over bootstrap draws and reports the fraction above zero and percentile interval. The first package uses 120 draws in the code version; the WPL-upgrade package changed this to 40 screening draws for runtime. These are not high-precision final intervals; use at least 1,000 draws for final reporting.", "BodyX"),
            P("9. Eligibility thresholds", "H1X"),
            make_table([
                ["Standard","Pressure matches","Normal matches","Pressure balls","Normal balls"],
                ["Relaxed","5","5","40","75"],
                ["Current","8","8","60","100"],
                ["Strict","12","12","100","150"],
            ], [34*mm,34*mm,34*mm,34*mm,34*mm]),
            P("A player must meet all four minimums. Relaxed increases coverage, Current is the primary balance point, and Strict tests rankings among players with greater exposure. These are heuristic starting thresholds, not statistically optimized cut-offs. The sensitivity report compares Top 10 membership with the Current list.", "BodyX"),
            P("10. Ranking order and outputs", "H1X"),
            P("Eligible players are ordered by EB lift, then bootstrap probability positive, lower confidence bound, raw lift and pressure-match count. The pipeline exports separate batter and bowler Top 10 files for each eligibility level, all-player score tables and a threshold-sensitivity table.", "BodyX"),
            P("11. Limitations and responsible interpretation", "H1X"),
            *bullets([
                "Pressure is a modelled situational-demand construct, not a direct psychological measurement.",
                "The component weights and eligibility thresholds are design hypotheses; they require ablation, sensitivity and expert review.",
                "The first-version WPL and first-innings par are proxies and should not be presented as full probabilistic leverage or a state-conditioned par model.",
                "The model's predictions depend on the correctness of extras, wicket, target, revised-overs and match-winner fields.",
                "T20 and T20I formats may differ; combined rankings should be accompanied by format-specific robustness checks.",
                "Bootstrap intervals in the packaged code are screening estimates, not definitive inferential intervals."
            ]),
            P("12. Judge-ready summary", "H1X"),
            P("“CLUTCH IQ compares players' actual performance with context-aware expected performance, separating high-pressure from normal situations. Its first version constructs pressure from match-state difficulty, a win-probability uncertainty proxy, resource scarcity, recent situational stress and innings progression. Batter and bowler pressure are modelled separately. Player estimates are shrunk to reduce small-sample extremes and are checked under relaxed, current and strict eligibility standards. All predictions are generated chronologically to reduce future-data leakage.”", "CalloutX"),
        ]
    else:
        story += [
            P("4. Expected-performance and win-probability models", "H1X"),
            P("The upgraded version retains the chronological expected-performance models for batter runs, bowler runs conceded and credited wicket probability, and the logistic win-probability model for batting-team match outcome. The scored-season predictions are out of sample: training uses earlier matches only.", "BodyX"),
            P("5. Upgraded WPL: expected next-delivery leverage", "H1X"),
            P("The upgraded version replaces the first-version state-sensitivity proxy with an expected absolute win-probability movement over a modelled distribution of possible next-delivery outcomes.", "BodyX"),
            P("WPL(S) = Σ<sub>o</sub> P(o | S) × |WP(S<sub>o</sub>) − WP(S)|", "FormulaX"),
            P("S is the current pre-delivery state. o is a possible joint delivery outcome. P(o|S) is its conditional probability. WP(S) is batting-team win probability before the delivery, and WP(Sₒ) is the predicted win probability after simulating outcome o. This is an expected leverage measure: it is high when plausible outcomes are expected to move win probability substantially.", "BodyX"),
            P("5.1 Outcome space", "H2X"),
            P("Each outcome class jointly represents: team runs in bins 0,1,2,3,4,5,6 or 7+; wicket indicator 0/1; and legal-ball indicator 0/1. The joint outcome class is encoded as:", "BodyX"),
            P("OutcomeClass = RunBin × 4 + Wicket × 2 + LegalFlag<br/>RunBin ∈ {0,1,2,3,4,5,6,7+}; Wicket ∈ {0,1}; LegalFlag ∈ {0,1}", "FormulaX"),
            P("There are 8 × 2 × 2 = 32 possible classes. The model uses joint outcomes so it does not assume runs, wickets and legal-ball status are independent.", "BodyX"),
            P("5.2 Conditional outcome probabilities and smoothing", "H2X"),
            P("The historical distribution is estimated from training-fold deliveries only. The state grouping variables are format, innings, phase, wickets-lost band and required-run-rate band. Wickets-lost bands are 0–2, 3–5 and 6–10; RRR bands are ≤6, 6–10, 10–14 and >14 (the code uses non-overlapping cut intervals).", "BodyX"),
            P("P(o | g) = [Count(g,o) + 40 × Pglobal(o)] / [Count(g) + 40]", "FormulaX"),
            P("Pglobal(o) is the fold-wide outcome probability with 0.5 pseudo-count smoothing for each of 32 classes: Pglobal(o) = [GlobalCount(o)+0.5]/[N+16]. The 40 pseudo-deliveries shrink sparse state groups toward the global distribution. If a state group is unseen, the global distribution is used.", "BodyX"),
            P("5.3 Simulating each outcome", "H2X"),
            P("For each possible outcome with non-negligible probability, the code updates score, wickets, legal balls, balls remaining, phase fraction, current run rate and chase requirements. It then predicts WP from the simulated state. Terminal chase states are overridden: a successful chase has WP=1; all-out or exhausted-ball failure has WP=0.", "BodyX"),
            P("5.4 WPL normalization", "H2X"),
            P("The raw expected movement is divided by the 95th percentile of raw WPL in a training-fold calibration sample and clipped to [0,1]. The scale is carried forward to the scored fold; the scored fold is not used to choose its own scale.", "BodyX"),
            P("WPLscaled = clip(WPLraw / Q95<sub>train</sub>(WPLraw), 0, 1)", "FormulaX"),
            P("The WPL model still depends on both the win-probability model and the conditional outcome distribution. Calibration and subgroup diagnostics are therefore essential. It is an expected modelled movement, not the realized change from the actual next ball.", "CalloutX"),
            P("6. Upgraded first-innings par model", "H1X"),
            P("The upgraded par model replaces the season-average phase proxy with a fold-specific HistGradientBoostingRegressor trained on first-innings pre-delivery states from earlier matches. It predicts the score expected at the current state.", "BodyX"),
            P("ParHat(S) = f(format, legalBallsBefore, wicketsBefore, inningsBallLimit, phaseFraction)", "FormulaX"),
            P("ParDeficit(S) = ParHat(S) − ScoreBefore(S)", "FormulaX"),
            P("The feature inputs are format code, legal balls already bowled, wickets lost, innings length and phase fraction. The target is score_before, so the model learns the expected score at that point in the innings, not the final innings total. The model is trained only on first-innings rows with valid decisive-match winner labels in the training fold.", "BodyX"),
            P("6.1 Temporal calibration offset", "H2X"),
            P("Within the training fold, dates are sorted. The earliest 85% of training dates fit a calibration model; the latest 15% provide a temporal calibration slice. If sample-size conditions are met, the mean residual in the calibration slice is used as an intercept offset:", "BodyX"),
            P("Offset = mean(ActualScoreBefore − PredictedScoreBefore) on calibration dates<br/>ParHatCalibrated = ParHat + Offset", "FormulaX"),
            P("The final par model is then refit on all training-fold first-innings rows, and the offset is applied to predictions in the next scored season. The scored season is not used to fit the model or its offset.", "BodyX"),
            P("6.2 Interpreting par error", "H2X"),
            P("Par MAE = mean(|PredictedPar − ActualScoreBefore|)<br/>Par Bias = mean(PredictedPar − ActualScoreBefore)", "FormulaX"),
            P("Positive bias means par is overpredicted on average; negative bias means par is underpredicted. Errors should be inspected by format, phase and wickets-lost group, not only as one aggregate number.", "BodyX"),
            P("7. Upgraded pressure construction", "H1X"),
            P("The MSD, RSI, SSI and PEP equations remain the same as the first version, but the first-innings ParScoreDeficit input is now the chronological model estimate and WPL is the expected-outcome WPL above.", "BodyX"),
            P("Chase MSD", "H2X"),
            P("RRRStress = clip((RRR − CRR) / 8, 0, 1)<br/>WicketStress = clip((10 − WicketsRemaining)/10, 0, 1)<super>1.5</super><br/>MSD = 0.60×RRRStress + 0.40×WicketStress", "FormulaX"),
            P("First-innings MSD", "H2X"),
            P("ParStress = clip(max(ParDeficit,0)/18, 0, 1)<br/>MSD = 0.65×ParStress + 0.35×WicketStress", "FormulaX"),
            P("RSI", "H2X"),
            P("RSI = 1 − [(BallsRemaining / InningsBallLimit) × (WicketsRemaining / 10)]", "FormulaX"),
            P("SSI", "H2X"),
            P("SSI = 0.35×CollapseStress + 0.30×RecoveryRequirement + 0.20×PartnershipDependency + 0.15×CriticalOverFlag", "FormulaX"),
            P("PEP", "H2X"),
            P("PEP = PhaseFraction × max(MSD, 0.5×RSI)", "FormulaX"),
            P("HDPI", "H2X"),
            P("HDPI = 100 × (0.25×MSD + 0.30×WPLscaled + 0.20×RSI + 0.15×SSI + 0.10×PEP)", "FormulaX"),
            P("The pressure bands and ≥60 high-pressure flag remain unchanged. The component weights remain design assumptions and should be tested through ablation and sensitivity analysis.", "BodyX"),
            P("8. Role-specific pressure scores", "H1X"),
            P("BPI = 100 × (0.35×HDPI/100 + 0.25×BatterUrgency + 0.20×DismissalRisk + 0.20×BatterResponsibility)<br/>BoPI = 100 × (0.35×HDPI/100 + 0.25×BowlerDefenceUrgency + 0.20×WicketThreat + 0.20×BowlerResponsibility)", "FormulaX"),
            P("BPI/BoPI inputs and their sub-formulas are unchanged from the first version. Batter pressure is BPI ≥60; bowler pressure is BoPI ≥60. These are role-specific situational-demand indices, not direct psychological measurements.", "BodyX"),
            P("9. Expected-performance residuals and ranking", "H1X"),
            P("BatterResidual = ActualRuns − ExpectedBatterRuns<br/>BowlerResidual = ExpectedConcededRuns − ActualConcededRuns<br/>WeightedResidual = Residual × (RolePressureScore/100)<super>1.5</super>", "FormulaX"),
            P("Rates are computed per 100 batter balls faced or bowler legal balls. Pressure lift is the pressure rate minus normal rate. Empirical-Bayes shrinkage and match-cluster bootstrap are applied as in the first version. In this upgrade package, the bootstrap uses 40 draws for screening/runtime; increase to at least 1,000 for final inferential reporting.", "BodyX"),
            P("10. Eligibility thresholds and outputs", "H1X"),
            make_table([
                ["Standard","Pressure matches","Normal matches","Pressure balls","Normal balls"],
                ["Relaxed","5","5","40","75"],
                ["Current","8","8","60","100"],
                ["Strict","12","12","100","150"],
            ], [34*mm,34*mm,34*mm,34*mm,34*mm]),
            P("Each player must meet all four requirements. The same thresholds are used to make the three leaderboard versions comparable between the two approaches.", "BodyX"),
            P("11. Validation results recorded in the upgrade report", "H1X"),
            make_table([
                ["Season","WP Brier","WP Log loss","WP ROC-AUC","WP ECE","Par MAE","Par bias"],
                ["2022","0.1728","0.5691","0.8207","0.0265","11.14","+1.72"],
                ["2023","0.1895","0.5597","0.7887","0.0464","11.62","−3.47"],
                ["2024","0.1853","0.5414","0.7930","0.0191","13.51","−0.40"],
                ["2025","0.1714","0.5034","0.8231","0.0291","13.80","−2.82"],
                ["2026","0.1869","0.5439","0.7914","0.0403","15.41","−9.94"],
            ], [20*mm,23*mm,23*mm,23*mm,20*mm,20*mm,20*mm]),
            P("The par model shows increasing underprediction in later seasons, especially 2026 (bias −9.94 runs). This should be investigated by format, phase, wickets and scoring environment. Do not describe par as perfectly calibrated.", "CalloutX"),
            P("12. What changed versus the first version?", "H1X"),
            make_table([
                ["Component","Fresh version","WPL + Par upgrade"],
                ["WPL","4×WP×(1−WP)×max(MSD,0.35×RSI), a state-sensitivity proxy.","Expected absolute WP movement across 32 joint next-delivery outcome classes; past-only conditional frequencies; fold-specific Q95 scaling."],
                ["First-innings par","Season-format average final total × phase fraction.","Chronological state model predicts score_before from format, balls elapsed, wickets lost, innings limit and phase; temporal calibration offset."],
                ["Other pressure dimensions","MSD, RSI, SSI, PEP; role-specific BPI/BoPI.","Same equations; upgraded WPL and par feed into them."],
                ["Thresholds","Relaxed 5/5/40/75; Current 8/8/60/100; Strict 12/12/100/150.","Unchanged, enabling direct threshold comparison."],
            ], [30*mm,70*mm,70*mm]),
            P("13. Limitations and judge-ready interpretation", "H1X"),
            *bullets([
                "The upgraded WPL is model-based expected leverage, not the actual next-ball WP movement. It relies on WP calibration and sufficient conditional outcome data.",
                "The outcome distribution uses 32 joint classes and a smoothing prior; sparse subgroups can still be uncertain.",
                "The par model is state-conditioned but its reported later-season bias shows calibration drift. Review by format, phase and wickets lost.",
                "The 2026 holdout should remain untouched for selecting weights or tuning the model; otherwise it ceases to be a final holdout.",
                "The weights, pressure cut-off and eligibility thresholds remain hypotheses to be validated through ablation and sensitivity studies.",
                "The package's 40 bootstrap draws are screening-only; use at least 1,000 and consider a stratified season-format match-cluster design for final intervals."
            ]),
            P("“The upgraded CLUTCH IQ approach replaces two coarse proxies with explicit historical models. WPL is calculated as the expected absolute change in batting-team win probability across a past-only distribution of possible joint delivery outcomes. First-innings par is estimated from a chronological model of the current score state, conditioned on format, balls elapsed, wickets lost and innings length. These improvements make pressure estimation more state-aware and interpretable, while chronological validation and reported calibration errors make the remaining uncertainty visible.”", "CalloutX"),
        ]
    return story

def build_pdf(path, title, subtitle, tag, upgraded=False):
    doc=SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                          topMargin=21*mm, bottomMargin=20*mm,
                          title=title, author="CLUTCH IQ Research")
    story=cover(title,subtitle,tag)
    story=add_common_sections(story,upgraded)
    doc.build(story,onFirstPage=page_decor,onLaterPages=page_decor)

p1=OUTDIR/"CLUTCH-IQ-2.0-FRESH-Methodology.pdf"
p2=OUTDIR/"CLUTCH-IQ-2.0-WPL-PAR-UPGRADE-Methodology.pdf"
build_pdf(p1,"Fresh methodology","Original CLUTCH-IQ-2.0-FRESH approach: baseline pressure architecture, proxy WPL, phase-level par proxy, expected performance and ranking methodology.","APPROACH 01 · FRESH",False)
build_pdf(p2,"WPL + Par upgrade methodology","Upgraded approach: expected next-delivery win-probability leverage and chronological first-innings par modelling, with the remaining pressure and ranking framework retained.","APPROACH 02 · UPGRADED",True)
print(p1, p1.stat().st_size, p2, p2.stat().st_size)
