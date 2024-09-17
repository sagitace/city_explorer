/** @type {import('tailwindcss').Config} */
module.exports = {
	content: [
		"./app/templates/**/*.html",
		"./app/static/src/**/*.js,",
		"./node_modules/flowbite/**/*.js",
	],
	theme: {
		extend: {
			fontFamily: {
				display: ["Roboto", "sans-serif"],
			},
		},
	},
	plugins: [require("flowbite/plugin")],
};
