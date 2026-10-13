/* ============================================================
   Marula Table Catering — front-end behaviour
   Flask injects window.APP_CONFIG (endpoint + email).
   ============================================================ */

const CONFIG = Object.assign(
  { endpoint: "/api/enquiry", email: "events@marulatable.co.za" },
  window.APP_CONFIG || {}
);

/* ------------------------------------------------------------ mobile nav */
const toggle = document.querySelector(".nav-toggle");
const nav = document.getElementById("nav");

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  nav.addEventListener("click", e => {
    if (e.target.tagName === "A") {
      nav.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
}

/* ------------------------------------------------------------ work filter */
const chips = document.querySelectorAll(".chip");
const works = document.querySelectorAll(".work");

chips.forEach(chip => {
  chip.addEventListener("click", () => {
    chips.forEach(c => {
      c.classList.remove("is-active");
      c.setAttribute("aria-pressed", "false");
    });
    chip.classList.add("is-active");
    chip.setAttribute("aria-pressed", "true");

    const f = chip.dataset.filter;
    works.forEach(w => {
      w.hidden = !(f === "all" || w.dataset.type === f);
    });
  });
});

/* ------------------------------------------------------------ menu switcher */
const menuButtons = document.querySelectorAll(".menu-nav-item");
const menuPanels  = document.querySelectorAll(".menu-panel-inner");

menuButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    const slug = btn.dataset.menu;
    menuButtons.forEach(b => {
      const on = b === btn;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", String(on));
    });
    menuPanels.forEach(p => {
      p.classList.toggle("is-hidden", p.dataset.panel !== slug);
    });
  });
});

/* ------------------------------------------------------------ enquiry form */
const form = document.getElementById("enquiryForm");

if (form) {
  const errBox = document.getElementById("formError");
  const okBox = document.getElementById("formSuccess");
  const dateInput = form.elements.date;

  // Today onwards, in both the picker and the native constraint.
  const today = new Date().toISOString().split("T")[0];
  dateInput.min = today;

  form.addEventListener("submit", async e => {
    e.preventDefault();
    errBox.hidden = true;

    /* ---- required-field pass (mirrors any server-side rules) ---- */
    const missing = [];
    form.querySelectorAll("[required]").forEach(el => {
      const bad =
        !el.value.trim() ||
        (el.type === "email" && !/^\S+@\S+\.\S+$/.test(el.value));
      el.setAttribute("aria-invalid", String(bad));
      if (bad) missing.push(el);
    });

    if (missing.length) {
      const names = missing
        .map(m => {
          const label = m.closest("label");
          return label ? label.firstChild.textContent.trim() : m.name;
        })
        .join(", ");
      errBox.textContent = "Please complete the highlighted fields: " + names + ".";
      errBox.hidden = false;
      missing[0].focus();
      return;
    }

    /* ---- assemble the payload ---- */
    const data = Object.fromEntries(new FormData(form));
    data.diet =
      [...form.querySelectorAll('[name="diet"]:checked')]
        .map(c => c.value)
        .join(", ") || "None specified";

    /* ---- send ---- */
    if (CONFIG.endpoint) {
      try {
        const res = await fetch(CONFIG.endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json"
          },
          body: JSON.stringify(data)
        });

        if (!res.ok) {
          errBox.textContent =
            "We couldn't send your enquiry. Please try again or email " +
            CONFIG.email + ".";
          errBox.hidden = false;
          return;
        }
      } catch {
        errBox.textContent =
          "We couldn't reach the server. Please try again or email " +
          CONFIG.email + ".";
        errBox.hidden = false;
        return;
      }
    } else {
      /* no endpoint: open the visitor's mail client */
      const body = Object.entries({
        Company: data.company,
        Name: data.name,
        Email: data.email,
        Phone: data.phone,
        "Event type": data.eventType,
        Date: data.date,
        Guests: data.guests,
        "Budget per person": data.budget || "Not sure",
        Venue: data.venue || "-",
        Dietary: data.diet,
        Notes: data.message || "-"
      })
        .map(([k, v]) => k + ": " + v)
        .join("\n");

      window.location.href =
        "mailto:" +
        CONFIG.email +
        "?subject=" +
        encodeURIComponent("Catering enquiry: " + data.company) +
        "&body=" +
        encodeURIComponent(body);
    }

    /* ---- success ---- */
    form.hidden = true;
    okBox.hidden = false;
    okBox.focus();
  });
}
/* ---------------------------------------------------------- footer year */
const yearEl = document.getElementById("year");
if (yearEl) yearEl.textContent = new Date().getFullYear();
/* ---------------------------------------------------------- scroll reveal */
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("is-visible");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });

document.querySelectorAll(".reveal, .reveal-stagger").forEach(el => {
  revealObserver.observe(el);
});

const timeline = document.querySelector(".timeline");
if (timeline) {
  const tlObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add("is-visible");
        tlObserver.unobserve(e.target);
      }
    });
  }, { threshold: 0.2 });
  tlObserver.observe(timeline);
}

/* ---------------------------------------------------------- stat count-up */
function animateCount(el, target, duration = 1400) {
  const match = String(target).match(/^([\d,]+)(.*)$/);
  if (!match) return;
  const numeric = parseInt(match[1].replace(/,/g, ""), 10);
  const suffix = match[2] || "";
  const useComma = match[1].includes(",");

  const start = performance.now();
  function tick(now) {
    const p = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = Math.floor(eased * numeric);
    el.textContent = (useComma ? val.toLocaleString("en-ZA") : val) + suffix;
    if (p < 1) requestAnimationFrame(tick);
    else el.textContent = (useComma ? numeric.toLocaleString("en-ZA") : numeric) + suffix;
  }
  requestAnimationFrame(tick);
}

const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = entry.target;
      if (el.dataset.count) animateCount(el, el.dataset.count);
      statsObserver.unobserve(el);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll("[data-count]").forEach(el => {
  statsObserver.observe(el);
});

/* ---------------------------------------------------------- header shadow */
const header = document.querySelector(".site-header");
if (header) {
  const onScroll = () => {
    header.classList.toggle("is-scrolled", window.scrollY > 20);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}