[LuxeStay-README.md](https://github.com/user-attachments/files/29676340/LuxeStay-README.md)
# LuxeStay 🏨

A hotel reservation website built as a team project for **CMPE312 (Software Engineering)** at Eastern Mediterranean University.

LuxeStay covers the full booking journey of a modern hotel platform: browsing and searching hotels, viewing room details, a 3-step checkout flow, booking confirmation, and a user dashboard with reservations, saved hotels, and rewards.

## Pages

| Section | What's inside |
|---|---|
| `home/` | Landing page with search, featured hotels, and destinations |
| `hotels/` | Search results and hotel detail pages (gallery, rooms, amenities, reviews) |
| `checkout/` | 3-step booking flow: room selection → guest details → payment |
| `dashboard/` | My Bookings, saved hotels, profile settings, rewards |
| `auth/` | Login, sign-up, and password recovery |
| `destinations/`, `offers/`, `about/`, `contact/` | Supporting content pages |
| `shared/css/` | Shared design tokens and layout styles |

## Design

Every screen was designed in **Figma** first — 20+ frames covering the complete user flow — then implemented as a responsive multi-page site in plain **HTML and CSS**. The visual identity uses a teal (`#1A7A6E`) and warm off-white (`#FDF6F0`) palette.

The project also includes a full **SRS document** (requirements, UML diagrams, and the end-to-end booking flow) written as part of the course deliverables.

## Running locally

No build step — it's a static site:

```bash
git clone https://github.com/ErenCAkpinar/LuxeStay.git
open LuxeStay/luxestay_website/home/html/index.html
```

## My role

I owned the UI/UX side: Figma designs for all screens and the HTML/CSS implementation. Team members contributed to other course deliverables (see branches).

## Roadmap

- [ ] Rebuild as a full-stack app: Next.js + TypeScript, Supabase auth, Stripe test-mode checkout
- [ ] Hotel search backed by a real database
- [ ] Deploy on Vercel
