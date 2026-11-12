# MEMO: Where to act first on late deliveries

**To:** VP Operations (hypothetical sponsor)
**From:** Business Analyst, Delivery Performance review
**Re:** Prioritised operational improvements to reduce delivery delays and improve customer satisfaction
**Basis:** 96,203 delivered orders, Jan 2017 – Aug 2018 (Olist public dataset). All figures are reproducible from the project repository.

---

### Recommendation
**Fund three interventions, in this order, and run the largest as a measured pilot before scaling:**

1. **Lane recovery pilot** on the lanes that underperform even after allowing for distance, starting with **São Paulo → Rio de Janeiro**.
2. **Peak-season playbook** in place before November.
3. **Seller deadline alerts and performance plans** for 57 sellers (quick win; start in week 1).

Alongside these, appoint one owner for delivery-promise reliability, review a single dashboard weekly, and **start recording the carrier on every order**. Without that data, the main source of delay cannot be attributed.

### Why
- **The problem is concentrated, so it is addressable.** 6.8% of delivered orders miss their promised date. Three months produced 48% of all late orders, and 15 lanes produced 88% of the excess late orders while carrying only 22% of volume.
- **The main delay happens after the seller hands over.** 72% of late orders left the seller on time. Seller deadline misses are a real but secondary driver (28%), and when they occur the late rate quadruples (21% vs. 5%).
- **SP → RJ is the single largest opportunity, and distance does not explain it.** It carries 8,031 orders at a 14.3% late rate, against 5.25% expected for orders travelling the same distance. Rio de Janeiro customers generate 13% of revenue.
- **The lane problem is persistent, not a fluke.** SP→RJ ran about 2× the platform late rate in both 2017 and 2018, and every one of 2017's ten worst lanes was still above average in 2018.
- **Late deliveries are strongly linked to bad reviews.** 62% of late orders get a 1–2 star review, against 9% of on-time orders. The gap holds within the same seller (53 pp) and after controlling for price, freight, state, category and month (51 pp). With 97% of customers buying only once, reviews are what new buyers see, and 2018 revenue had plateaued.

### What it could achieve (scenario, not forecast)
If each lever removes half of the problem it targets (40% for peaks), the late rate in the baseline year falls from **7.9% to 5.3%** (range 6.4% to 4.3%). That means about **1,800 fewer late orders a year**. If the review link is causal, the 1–2 star rate would fall from 12.9% to about 11.6%. If the unexplained Feb–Mar 2018 spike does not recur, and so cannot be planned for, the base case is about **6.1%**. **Reaching 5% needs better-than-base execution**, so I propose a staged target: **≤ 6% within two quarters, ≤ 5% within twelve months**, re-based once the pilot measures the real effect.

### What I am *not* recommending
- **Lengthening delivery promises.** Tested out of sample, it barely helps at equal promise length (7.83% → 7.45%), and it risks conversion.
- **Retention campaigns tied to late deliveries.** The repeat-purchase effect is real but small (about 46 customers over 20 months).
- **Any ROI figure.** The data contains no cost or margin. Finance input is required to convert these outcomes into money.

### Key risks
- The review effect may be smaller than the association suggests, because causality is not proven. *Mitigation:* a staggered lane pilot with control lanes.
- The 2017–18 data may not reflect current operations. *Mitigation:* rerun the reproducible pipeline on current data in week 1.
- Promise inflation could be used to game the KPI. *Mitigation:* average promised days is a guardrail.

### Decision requested
Approve (1) the week-1 start of the seller alerts and the weekly delivery review, (2) a 3–4 month lane pilot on SP→RJ and SP→ES with control lanes, and (3) the carrier-ID data capture.

*Supporting detail: `docs/06_insights_and_evidence.md` (findings and evidence grades), `docs/08_scenario_analysis.md` (assumptions), `docs/11_risk_register.md`.*
