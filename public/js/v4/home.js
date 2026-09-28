/** Home (v0.7): the journey home replaces the old career picker. One person,
 * one small neighbourhood; workplaces open chapter by chapter. Everything
 * lives in journey.js; this module keeps app.js imports stable. Buttons keep
 * the app's `choose` (data-career), `close` and `homeCat` actions. */
export {journeyHome as homeView,journeyFuture as futureView,journeyBoot,journeyAction,journeySubmit} from './journey.js';
